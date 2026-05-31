"""
Configuration — Pengaturan global untuk NeuroMotorik Screener Server.

Catatan: Threshold klinis sekarang berada di core/clinical_thresholds.py
         (evidence-based dari literatur medis).
"""

import os

# ── Server ──────────────────────────────────────────────
HOST = os.getenv("SERVER_HOST", "0.0.0.0")
PORT = int(os.getenv("SERVER_PORT", "8765"))

# ── Database ────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "neuromotorik.db")

# ── Auth & Security ──────────────────────────────────────
API_KEY = os.getenv("NMS_API_KEY", "neuromotorik-default-key")
JWT_SECRET = os.getenv("NMS_JWT_SECRET", "neuromotorik-jwt-secret-change-in-production")
JWT_EXPIRE_HOURS = int(os.getenv("NMS_JWT_EXPIRE_HOURS", "24"))
DATA_RETENTION_DAYS = int(os.getenv("NMS_DATA_RETENTION_DAYS", "90"))

# ── Pose Estimation ─────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.5    # Minimum landmark visibility
ANALYSIS_FPS = 30             # Frame rate target
FRAME_SKIP = 2                # Analisis setiap N frame
