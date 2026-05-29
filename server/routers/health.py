"""
Health Check endpoint — Status server, CPU, memory.
"""

import time
try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

from fastapi import APIRouter

router = APIRouter()
_start_time = time.time()


@router.get("/")
async def health():
    data = {
        "status": "ok",
        "service": "NeuroMotorik Screener",
        "version": "1.0.0",
        "uptime_seconds": round(time.time() - _start_time, 1),
    }
    if _HAS_PSUTIL:
        data["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        data["memory_mb"] = round(psutil.Process().memory_info().rss / 1024 / 1024, 1)
    return data
