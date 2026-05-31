# NeuroMotorik Screener

![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-teal)
![MediaPipe](https://img.shields.io/badge/MediaPipe-Pose-orange)

Web-based clinical screening tool for early detection of neuro-motoric disorders — **Stroke**, **Parkinson's**, and **Sarcopenia** — using real-time pose estimation via webcam.

Browser captures body landmarks with **Google MediaPipe Pose**, streams them over **WebSocket** to a **FastAPI** backend, where the **Kinematic Engine** computes clinical metrics and risk classifications.

---

## Features

| Assessment | Metric | Detects |
|---|---|---|
| Raise Hands | Asymmetry Index (ASI) | Stroke risk |
| Stand Still | Power Spectral Density (PSD) | Parkinson's / tremor |
| Sit-to-Stand | STS transition speed | Sarcopenia risk |

- **Sequential assessment** — 3-in-1 automated flow (stroke → parkinson → sarcopenia)
- **Rehabilitation mode** — gamified arm raise & squat exercises with real-time feedback
- **Simulation mode** — synthetic landmark generation, no camera needed
- **PDF reports** — server-side (reportlab) and client-side fallback (jsPDF)
- **Auth** — API key → JWT token flow
- **GDPR-compliant data deletion** — patient data purge endpoint
- **Calibration** — shoulder-width anthropometric reference, perspective correction

---

## Quick Start

### Prerequisites

- Python 3.9+
- Webcam
- Node.js (optional, for Vite dev server)

### Backend

```bash
cd server
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Server starts at `http://0.0.0.0:8765`. Serves frontend too.

### Frontend (optional)

```bash
cd client && npx vite    # → http://localhost:5173
```

Or just open `http://localhost:8765` — backend serves `client/` as static files.

### Docker (alternative)

```bash
docker build -t neuromotorik .
docker run -p 8765:8765 neuromotorik
```

---

## Usage

1. Open the app in a browser.
2. Enter **Patient ID** and **Age** (age stratifies sarcopenia thresholds).
3. Select an assessment type or start **Sequential Assessment**.
4. Click **Start** — grant camera access.
5. Stand in frame until skeleton overlay appears.
6. Follow on-screen instructions. Real-time ASI/PSD charts update live.
7. After session ends, view the **Clinical Report** with risk classification.
8. Export as PDF or review via REST API.

---

## Architecture

```
Browser (webcam + MediaPipe Pose)
        │
        ▼ WebSocket /ws/stream
  ┌─────────────┐
  │  FastAPI     │ ← REST API /api/*
  │  Server      │ ← Auth /api/auth/*
  │  :8765       │ ← Simulation /api/sim/*
  └─────┬───────┘
        │
        ▼
  KinematicEngine (per session)
   ├─ asymmetry_index.py      ASI calculation
   ├─ tremor_analyzer.py       PSD / FFT tremor detection
   ├─ sit_to_stand.py          STS transition timing
   ├─ clinical_thresholds.py   Evidence-based cutoff values
   ├─ risk_classifier.py       Weighted → RiskLevel
   └─ calibration.py           Distance normalization
```

### Server

| Path | Purpose |
|---|---|
| `server/main.py` | Entry point, lifespan, CORS, static mount |
| `server/config.py` | Env-driven config |
| `server/core/kinematic_engine.py` | Per-session engine: landmarks → metrics → report |
| `server/core/asymmetry_index.py` | ASI computation |
| `server/core/tremor_analyzer.py` | FFT-based tremor frequency analysis |
| `server/core/sit_to_stand.py` | STS transition detection |
| `server/core/clinical_thresholds.py` | Frozen dataclasses — stroke/ASI, parkinson/tremor, sarcopenia/STS |
| `server/core/risk_classifier.py` | Weighted scoring → `normal` / `monitor` / `referral` |
| `server/core/calibration.py` | Shoulder-width anthropometric scale |
| `server/core/angle_calculator.py` | Joint angle computation |
| `server/core/session_manager.py` | Active session tracking |
| `server/core/security.py` | JWT, API key auth, patient ID sanitization |
| `server/core/simulation.py` | Synthetic landmark generator |
| `server/core/validation.py` | Benchmark validation |
| `server/routers/ws_handler.py` | WebSocket endpoint |
| `server/routers/api_routes.py` | REST: reports, history, stats, PDF, data deletion |
| `server/routers/auth_routes.py` | `/api/auth/login`, `/api/auth/verify` |
| `server/routers/simulation_routes.py` | `/api/sim/start`, `/api/sim/{id}/replay` |
| `server/routers/tts_handler.py` | Text-to-speech |
| `server/routers/health.py` | Health check |
| `server/models/schemas.py` | Pydantic models: `Landmark`, `KinematicMetrics`, `ClinicalReport` |
| `server/models/database.py` | Thread-safe SQLite singleton (WAL mode) |
| `server/models/replay.py` | Session replay models |
| `server/services/pdf_generator.py` | Server-side PDF (reportlab) |
| `server/services/report_generator.py` | Report dict from `ClinicalReport` |

### Client

| Path | Purpose |
|---|---|
| `client/js/main.js` | App controller: camera, UI, sequential assessment, rehab mode |
| `client/js/websocket-client.js` | WS client with auto-reconnect |
| `client/js/skeleton-renderer.js` | MediaPipe Pose canvas rendering |
| `client/js/chart-manager.js` | Chart.js real-time graphs (ASI, PSD) |
| `client/js/calibration.js` | Client-side calibration (shoulder-width estimation) |
| `client/js/simulation.js` | SimRunner UI for demo mode |
| `client/js/pdf-export.js` | Client-side PDF fallback (jsPDF) |

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/auth/login` | Authenticate with API key → JWT |
| `GET` | `/api/auth/verify` | Verify JWT token |
| `GET` | `/api/reports/{session_id}` | Get report by session ID |
| `GET` | `/api/reports/{session_id}/pdf` | Export report as PDF |
| `GET` | `/api/reports` | List recent reports |
| `GET` | `/api/patients/{patient_id}/history` | Patient assessment history |
| `DELETE` | `/api/patients/{patient_id}/data` | GDPR data deletion |
| `GET` | `/api/sessions/{session_id}/replay` | Get raw landmark replay data |
| `DELETE` | `/api/sessions/{session_id}/replay` | Delete raw landmark data |
| `GET` | `/api/dashboard/stats` | Dashboard statistics |
| `POST` | `/api/sim/start` | Start simulation (no camera) |
| `GET` | `/api/sim/{simulation_id}/replay` | Simulation replay data |
| `WS` | `/ws/stream` | Real-time landmark streaming |

---

## Configuration

Environment variables (set or use defaults):

| Variable | Default | Description |
|---|---|---|
| `SERVER_HOST` | `0.0.0.0` | Bind address |
| `SERVER_PORT` | `8765` | Bind port |
| `DB_PATH` | `neuromotorik.db` | SQLite database path |
| `NMS_API_KEY` | `neuromotorik-default-key` | API key for auth |
| `NMS_JWT_SECRET` | `neuromotorik-jwt-secret-change-in-production` | JWT signing secret |
| `NMS_JWT_EXPIRE_HOURS` | `24` | JWT expiration |
| `NMS_DATA_RETENTION_DAYS` | `90` | Auto-purge threshold |

> **Warning:** Change `NMS_API_KEY` and `NMS_JWT_SECRET` before deploying to production.

WebSocket URL is hardcoded in `client/js/websocket-client.js` as `ws://127.0.0.1:8765/ws/stream`. Changing the server port requires updating this URL.

---

## Testing

```bash
cd server
python -m pytest tests/ -v
```

### Validation benchmark

```bash
cd server && python validation_runner.py
```

Runs 7 benchmark cases (normal symmetric, moderate/severe asymmetry, parkinsonian tremor, postural tremor, slow/normal STS) through the full engine. Reports PASS/FAIL per classification.

---

## Project Structure

```
Neurosight/
├── client/                          # Frontend — vanilla HTML/CSS/JS
│   ├── css/style.css
│   ├── js/
│   │   ├── main.js                  # App controller
│   │   ├── websocket-client.js       # WS client (auto-reconnect)
│   │   ├── skeleton-renderer.js      # MediaPipe Pose canvas
│   │   ├── chart-manager.js         # Chart.js real-time graphs
│   │   ├── calibration.js           # Shoulder-width calibration
│   │   ├── simulation.js            # SimRunner UI
│   │   └── pdf-export.js            # Client-side PDF fallback
│   └── index.html
│
├── server/                          # Backend — Python FastAPI
│   ├── core/                        # Clinical analysis engine
│   │   ├── kinematic_engine.py      # Per-session orchestrator
│   │   ├── asymmetry_index.py       # ASI computation
│   │   ├── tremor_analyzer.py        # FFT tremor detection
│   │   ├── sit_to_stand.py          # STS timing
│   │   ├── angle_calculator.py      # Joint angles
│   │   ├── clinical_thresholds.py   # Evidence-based cutoffs
│   │   ├── risk_classifier.py       # RiskLevel classification
│   │   ├── calibration.py           # Distance normalization
│   │   ├── session_manager.py       # Session tracking
│   │   ├── security.py              # JWT + API key auth
│   │   ├── simulation.py            # Synthetic data generator
│   │   └── validation.py           # Benchmark validation
│   ├── routers/
│   │   ├── ws_handler.py            # WebSocket endpoint
│   │   ├── api_routes.py            # REST API
│   │   ├── auth_routes.py           # Auth endpoints
│   │   ├── simulation_routes.py    # Simulation API
│   │   ├── tts_handler.py           # TTS
│   │   └── health.py                # Health check
│   ├── models/
│   │   ├── schemas.py               # Pydantic models
│   │   ├── database.py              # SQLite (WAL, thread-safe)
│   │   └── replay.py                # Replay models
│   ├── services/
│   │   ├── pdf_generator.py         # Server-side PDF
│   │   └── report_generator.py      # Report serializer
│   ├── tests/
│   ├── config.py                    # Env-driven config
│   ├── main.py                      # Entry point
│   ├── validation_runner.py         # CLI validation runner
│   └── requirements.txt
│
├── AGENTS.md                        # Agent documentation
└── .gitignore
```

---

## License

See [LICENSE](LICENSE) for details.