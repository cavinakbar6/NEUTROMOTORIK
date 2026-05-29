"""
NeuroMotorik Screener — FastAPI Application Entry Point.
Server lokal untuk skrining multi-anomali neuro-motorik.
"""

import os
import sys
import time
import signal
import uvicorn
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from routers.ws_handler import router as ws_router
from routers.api_routes import router as api_router
from routers.health import router as health_router
from config import HOST, PORT

# ── Path Setup ───────────────────────────────────────────
SERVER_DIR = Path(__file__).parent.resolve()
CLIENT_DIR = SERVER_DIR.parent / "client"


# ── Lifespan (startup/shutdown) ──────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup & shutdown events."""
    print()
    print("  +----------------------------------------------------+")
    print("  |   NeuroMotorik Screener Server v1.0                 |")
    print(f"  |   Listening on: http://{HOST}:{PORT}                  |")
    print(f"  |   Dashboard:    http://localhost:{PORT}               |")
    print("  |   Status:       [OK] Started                        |")
    print("  +----------------------------------------------------+")
    print()
    yield
    print("\n  [Server] Shutting down gracefully...")


# ── FastAPI App ──────────────────────────────────────────
app = FastAPI(
    title="NeuroMotorik Screener API",
    description="Server lokal skrining Stroke, Parkinson, Sarcopenia via webcam",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])
app.include_router(api_router, prefix="/api", tags=["API"])

# Static files (frontend) — harus diakhir
if CLIENT_DIR.exists():
    app.mount("/", StaticFiles(directory=str(CLIENT_DIR), html=True), name="client")
else:
    print(f"  [WARN] Client directory not found: {CLIENT_DIR}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
        access_log=False,
    )
