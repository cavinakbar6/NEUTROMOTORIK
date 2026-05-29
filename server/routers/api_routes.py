"""
REST API Routes — Untuk akses laporan, riwayat, dan statistik.
"""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from models.database import Database

router = APIRouter()
db = Database()


@router.get("/reports/{session_id}")
async def get_report(session_id: str):
    """Ambil laporan berdasarkan session ID."""
    row = db.get_report(session_id)
    if not row:
        raise HTTPException(404, detail="Report not found")
    return JSONResponse(content=json.loads(row[0]))


@router.get("/patients/{patient_id}/history")
async def get_patient_history(patient_id: str):
    """Ambil riwayat assessment seorang pasien."""
    rows = db.get_patient_history(patient_id)
    reports = []
    for rj, created_at in rows:
        try:
            data = json.loads(rj)
            data["created_at"] = created_at
            reports.append(data)
        except json.JSONDecodeError:
            continue
    return {
        "patient_id": patient_id,
        "total_sessions": len(reports),
        "reports": reports,
    }


@router.get("/reports")
async def list_reports(limit: int = 50):
    """List semua laporan terbaru."""
    rows = db.get_all_reports(limit=limit)
    reports = []
    for rj, created_at, pid, instr in rows:
        try:
            data = json.loads(rj)
            data["created_at"] = created_at
            data["patient_id"] = pid
            data["instruction"] = instr
            reports.append(data)
        except json.JSONDecodeError:
            continue
    return {"total": len(reports), "reports": reports}


@router.get("/dashboard/stats")
async def get_stats():
    """Statistik ringkas untuk dashboard."""
    return db.get_stats()
