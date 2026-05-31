# NeuroMotorik Screener — Agent Notes

## Architecture

Two-process app: **Python FastAPI backend** (`server/`) + **vanilla HTML/CSS/JS frontend** (`client/`). No build step for the client — it's plain JS with no bundler config; `npx vite` is just a dev server serving static files.

The backend also serves the client as static files at `/` (mounted last in `main.py`), so for production you only run the Python server.

**Data flow:** Browser webcam → MediaPipe Pose (client-side) → WebSocket `/ws/stream` → `KinematicEngine` (server-side) → real-time metrics back via WS + clinical report on session end. REST API at `/api/*` for report retrieval/history.

## Running

```bash
# Backend (required)
cd server
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py            # → http://0.0.0.0:8765

# Frontend dev server (optional, for live reload)
cd client && npx vite     # → http://localhost:5173
#  OR just open http://localhost:8765 directly (backend serves client/)

# Tests
cd server && python -m pytest tests/ -v

# Validation benchmark
cd server && python validation_runner.py
```

## Key conventions

- **WebSocket port is hardcoded** in `client/js/websocket-client.js` as `ws://127.0.0.1:8765/ws/stream`. Changing the server port requires updating this URL too.
- Server config (`server/config.py`) reads env vars: `SERVER_HOST`, `SERVER_PORT`, `DB_PATH`, `NMS_API_KEY`, `NMS_JWT_SECRET`, `NMS_JWT_EXPIRE_HOURS`, `NMS_DATA_RETENTION_DAYS`.
- `neuromotorik.db` (SQLite with WAL mode) is created at runtime in the server directory — it's in `.gitignore`.

## Server module map

| Path | Purpose |
|---|---|
| `server/main.py` | Entry point, lifespan, CORS, mounts client/ as static |
| `server/config.py` | Env-driven config (host, port, db path, auth, retention) |
| `server/routers/ws_handler.py` | WebSocket endpoint — all real-time comm |
| `server/routers/api_routes.py` | REST endpoints for reports/history/stats/PDF/data deletion |
| `server/routers/auth_routes.py` | API key auth → JWT tokens (`/api/auth/login`, `/api/auth/verify`) |
| `server/routers/simulation_routes.py` | Simulation mode REST API (`/api/sim/start`, `/api/sim/{id}/replay`) |
| `server/core/kinematic_engine.py` | Per-session engine: receives landmarks, produces metrics/reports |
| `server/core/clinical_thresholds.py` | Evidence-based threshold dataclasses (stroke/ASI, parkinson/tremor, sarcopenia/STS) |
| `server/core/risk_classifier.py` | Weighted scoring → RiskLevel enum (normal/monitor/referral) |
| `server/core/calibration.py` | Camera distance normalization (shoulder-width reference, perspective correction) |
| `server/core/simulation.py` | Synthetic landmark generation for demo/testing without camera |
| `server/core/validation.py` | Benchmark validation against known-expected-outcome synthetic data |
| `server/core/security.py` | JWT creation/verification, API key auth, patient ID sanitization |
| `server/services/pdf_generator.py` | Server-side PDF report generation (reportlab) |
| `server/services/report_generator.py` | Report dict generation from ClinicalReport |
| `server/models/schemas.py` | Pydantic models: `Landmark`, `KinematicMetrics`, `RehabMetrics`, `ClinicalReport` |
| `server/models/database.py` | Thread-safe SQLite singleton (patients, sessions, reports, consents, raw_landmarks) |
| `server/models/replay.py` | Pydantic models for session replay API |
| `server/validation_runner.py` | CLI to run validation benchmark (7 cases, prints PASS/FAIL report) |

## Client module map

| Path | Purpose |
|---|---|
| `client/js/main.js` | App controller: camera, UI, sequential assessment, rehab mode |
| `client/js/websocket-client.js` | WS client with auto-reconnect |
| `client/js/skeleton-renderer.js` | MediaPipe Pose rendering on canvas |
| `client/js/chart-manager.js` | Chart.js real-time graphs (ASI, PSD) |
| `client/js/calibration.js` | Client-side calibration (shoulder-width distance estimation) |
| `client/js/simulation.js` | SimRunner UI for demo mode without camera |
| `client/js/pdf-export.js` | Client-side PDF export fallback (jsPDF) |

## API routes

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login` | Authenticate with API key → JWT |
| GET | `/api/auth/verify` | Verify JWT token |
| GET | `/api/reports/{session_id}` | Get report by session ID |
| GET | `/api/reports/{session_id}/pdf` | Export report as PDF |
| GET | `/api/reports` | List recent reports |
| GET | `/api/patients/{patient_id}/history` | Get patient assessment history |
| DELETE | `/api/patients/{patient_id}/data` | GDPR-style data deletion |
| GET | `/api/sessions/{session_id}/replay` | Get raw landmark data for replay |
| DELETE | `/api/sessions/{session_id}/replay` | Delete raw landmark data |
| GET | `/api/dashboard/stats` | Dashboard statistics |
| POST | `/api/sim/start` | Start a simulation (no camera needed) |
| GET | `/api/sim/{simulation_id}/replay` | Get simulation replay data |
| WS | `/ws/stream` | Real-time landmark streaming |

## Important details

- **RiskLevel enum values** are `normal`, `monitor`, `referral` (correctly spelled).
- **Instruction types:** `raise_hands`, `stand_still`, `sit_to_stand` (clinical), `rehab_arm_raise`, `rehab_squat` (gamification). These are string values sent over WebSocket, not just DB labels.
- **Sequential assessment** (3-in-1) uses `sequential_start` → multiple `session_start/session_end` → `sequential_end` message flow. Each step resets the engine.
- **Age parameter** in `session_start` enables age-stratified sarcopenia thresholds. Without it, conservative defaults are used.
- Clinical thresholds are in `server/core/clinical_thresholds.py` as frozen dataclasses — changing thresholds requires editing that file.
- **Calibration**: `Calibrator` in `core/calibration.py` uses shoulder width (indices 11/12, ~40cm average) as anthropometric reference. Accumulates 30 frames then computes scale factor. Server sends calibration data (distance_m, confidence) in metrics when available.
- **Simulation mode**: `POST /api/sim/start` accepts `{instruction, scenario, duration_s, patient_age}` and runs the full pipeline with synthetic data. Scenarios: `normal`, `stroke_mild`, `stroke_severe`, `parkinson_tremor`, `sarcopenia_slow`.
- **Session replay**: Raw landmarks are batch-saved every 30 frames during a session, queryable via `/api/sessions/{id}/replay`.
- **Auth**: Simple API key → JWT. Default key is `neuromotorik-default-key` (change via `NMS_API_KEY` env var). JWTs expire in 24h by default.
- **Data retention**: `NMS_DATA_RETENTION_DAYS` env var (default 90). `Database.purge_expired_data(days)` deletes old sessions/reports.
- **Validation**: `python validation_runner.py` runs 7 benchmark cases (normal symmetric, moderate/severe asymmetry, parkinsonian tremor, postural tremor, slow/normal STS) through the full engine and reports PASS/FAIL per classification.