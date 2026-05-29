"""
SessionManager — Mengelola lifecycle sesi dan persistensi ke database.

Perbaikan:
  - Simpan report dalam format ReportGenerator.to_dict() (bukan ClinicalReport raw)
  - Sehingga database.get_stats() bisa parse risk_levels dengan benar
"""

import time
import json
import uuid
from typing import Dict, Optional
from models.database import Database
from models.schemas import ClinicalReport
from services.report_generator import ReportGenerator


class SessionManager:

    def __init__(self):
        self.db = Database()
        self.active: Dict[str, dict] = {}

    def create(self, patient_id: str, instruction: str, age: Optional[int] = None) -> str:
        """Buat sesi baru dan return session_id."""
        sid = str(uuid.uuid4())[:8]
        self.active[sid] = {
            "patient_id": patient_id,
            "instruction": instruction,
            "age": age,
            "started_at": time.time(),
        }
        self.db.create_session(sid, patient_id, instruction)
        return sid

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """Get info sesi aktif."""
        return self.active.get(session_id)

    def save_report(self, report: ClinicalReport, session_id: str) -> dict:
        """
        Simpan laporan dalam format terstruktur (ReportGenerator.to_dict()).
        Return: formatted report dict untuk dikirim ke client.
        """
        # Format report menggunakan ReportGenerator
        formatted = ReportGenerator.to_dict(report)

        # Simpan ke database dalam format yang bisa di-parse oleh get_stats()
        self.db.upsert_patient(report.patient_id, report.patient_id)
        self.db.save_report(
            report.session_id, session_id, json.dumps(formatted)
        )
        self.db.complete_session(session_id)
        self.active.pop(session_id, None)

        return formatted

    def get_active_count(self) -> int:
        return len(self.active)
