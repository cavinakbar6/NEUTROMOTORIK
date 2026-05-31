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
```

No test suite exists. No linter/formatter config. No CI.

## Key conventions

- **WebSocket port is hardcoded** in `client/js/websocket-client.js:13` as `ws://127.0.0.1:8765/ws/stream`. Changing the server port requires updating this URL too.
- Server config (`server/config.py`) reads `SERVER_HOST`, `SERVER_PORT`, `DB_PATH` from env vars with defaults (`0.0.0.0:8765`, `neuromotorik.db`).
- `neuromotorik.db` (SQLite with WAL mode) is created at runtime in the server directory — it's in `.gitignore`.

## Server module map

| Path | Purpose |
|---|---|
| `server/main.py` | Entry point, lifespan, CORS, mounts client/ as static |
| `server/config.py` | Env-driven config (host, port, db path, pose params) |
| `server/routers/ws_handler.py` | WebSocket endpoint — all real-time comm |
| `server/routers/api_routes.py` | REST endpoints for reports/history/stats |
| `server/core/kinematic_engine.py` | Per-session engine: receives landmarks, produces metrics/reports |
| `server/core/clinical_thresholds.py` | Evidence-based threshold dataclasses (stroke/ASI, parkinson/tremor, sarcopenia/STS) |
| `server/core/risk_classifier.py` | Weighted scoring → RiskLevel enum (normal/monitor/referal) |
| `server/models/schemas.py` | Pydantic models: `Landmark`, `KinematicMetrics`, `RehabMetrics`, `ClinicalReport` |
| `server/models/database.py` | Thread-safe SQLite singleton |

## Client module map

| Path | Purpose |
|---|---|
| `client/js/main.js` | App controller: camera, UI, sequential assessment, rehab mode |
| `client/js/websocket-client.js` | WS client with auto-reconnect |
| `client/js/skeleton-renderer.js` | MediaPipe Pose rendering on canvas |
| `client/js/chart-manager.js` | Chart.js real-time graphs (ASI, PSD) |

## Important details

- **RiskLevel enum value** is `"referal"` (not "referral") — this is intentional throughout the codebase. Don't "fix" the spelling.
- **Instruction types:** `raise_hands`, `stand_still`, `sit_to_stand` (clinical), `rehab_arm_raise`, `rehab_squat` (gamification). These are string values sent over WebSocket, not just DB labels.
- **Sequential assessment** (3-in-1) uses `sequential_start` → multiple `session_start/session_end` → `sequential_end` message flow. Each step resets the engine.
- **Age parameter** in `session_start` enables age-stratified sarcopenia thresholds. Without it, conservative defaults are used.
- Clinical thresholds are in `server/core/clinical_thresholds.py` as frozen dataclasses — changing thresholds requires editing that file.