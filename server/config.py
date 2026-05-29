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

# ── Pose Estimation ─────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.5    # Minimum landmark visibility
ANALYSIS_FPS = 30             # Frame rate target
FRAME_SKIP = 2                # Analisis setiap N frame
