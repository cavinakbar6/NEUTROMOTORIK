"""
REST API Routes — Untuk akses laporan, riwayat, dan statistik.
"""

import json
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from models.database import Database
from services.pdf_generator import generate_report_pdf
from core.security import sanitize_patient_id

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


@router.get("/reports/{session_id}/pdf")
async def export_report_pdf(session_id: str):
    """Export clinical report as PDF."""
    row = db.get_report(session_id)
    if not row:
        raise HTTPException(404, detail="Report not found")
    report_data = json.loads(row[0])
    pdf_bytes = generate_report_pdf(report_data)
    filename = f"neuromotorik-report-{session_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/patients/{patient_id}/data")
async def delete_patient_data(patient_id: str):
    """GDPR-style data deletion — removes all patient sessions and reports."""
    patient_id = sanitize_patient_id(patient_id)
    sessions = db.fetchall(
        "SELECT id FROM sessions WHERE patient_id=?", (patient_id,)
    )
    for (session_id,) in sessions:
        db.execute("DELETE FROM reports WHERE session_id=?", (session_id,))
    db.execute("DELETE FROM sessions WHERE patient_id=?", (patient_id,))
    db.execute("DELETE FROM consents WHERE patient_id=?", (patient_id,))
    db.execute("DELETE FROM patients WHERE id=?", (patient_id,))
    return {"deleted": True, "patient_id": patient_id}


@router.get("/sessions/{session_id}/replay")
async def get_session_replay(session_id: str):
    """Get raw landmark data for session replay."""
    from models.replay import LandmarkFrame, ReplayData
    import json

    session = db.fetchone("SELECT id FROM sessions WHERE id=?", (session_id,))
    if not session:
        raise HTTPException(404, detail="Session not found")

    rows = db.get_landmarks(session_id)
    if not rows:
        raise HTTPException(404, detail="No landmark data found for this session")

    frames = []
    for frame_number, timestamp, landmarks_json in rows:
        frames.append(LandmarkFrame(
            frame_number=frame_number,
            timestamp=timestamp,
            landmarks_json=landmarks_json,
        ))

    duration = frames[-1].timestamp - frames[0].timestamp if len(frames) > 1 else 0.0
    return ReplayData(
        session_id=session_id,
        frames=frames,
        total_frames=len(frames),
        duration_s=round(duration, 2),
    ).model_dump()


@router.delete("/sessions/{session_id}/replay")
async def delete_session_replay(session_id: str):
    """Delete raw landmark data to save storage."""
    session = db.fetchone("SELECT id FROM sessions WHERE id=?", (session_id,))
    if not session:
        raise HTTPException(404, detail="Session not found")
    db.delete_landmarks(session_id)
    return {"deleted": True, "session_id": session_id}


@router.get("/dashboard/stats")
async def get_stats():
    """Statistik ringkas untuk dashboard."""
    return db.get_stats()
