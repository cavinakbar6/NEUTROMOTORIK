"""
Database — SQLite persistence untuk pasien, sesi, dan laporan.
Thread-safe dengan WAL mode dan indexes.
"""

import json
import sqlite3
import threading
import uuid
from typing import Optional
from config import DB_PATH


class Database:
    """SQLite database wrapper — thread-safe singleton."""

    _instance: Optional["Database"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_db()
        return cls._instance

    def _init_db(self):
        self._db_path = DB_PATH
        self._conn = sqlite3.connect(
            self._db_path,
            check_same_thread=False,
            timeout=10,
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._create_tables()

    def _create_tables(self):
        c = self._conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                age         INTEGER DEFAULT 0,
                gender      TEXT DEFAULT '',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          TEXT PRIMARY KEY,
                patient_id  TEXT NOT NULL,
                instruction TEXT NOT NULL,
                status      TEXT DEFAULT 'active',
                started_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at    TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id          TEXT PRIMARY KEY,
                session_id  TEXT UNIQUE,
                report_json TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS consents (
                id          TEXT PRIMARY KEY,
                patient_id  TEXT NOT NULL,
                consent_type TEXT NOT NULL,
                granted_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at  TIMESTAMP,
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS raw_landmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                frame_number INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                landmarks_json TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)

        c.execute("CREATE INDEX IF NOT EXISTS idx_landmarks_session ON raw_landmarks(session_id)")

        # Indexes for faster queries
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_patient ON sessions(patient_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_reports_session ON reports(session_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_consents_patient ON consents(patient_id)")

        self._conn.commit()

    def execute(self, query: str, params: tuple = ()):
        with self._lock:
            cursor = self._conn.execute(query, params)
            self._conn.commit()
            return cursor

    def fetchone(self, query: str, params: tuple = ()):
        with self._lock:
            return self._conn.execute(query, params).fetchone()

    def fetchall(self, query: str, params: tuple = ()):
        with self._lock:
            return self._conn.execute(query, params).fetchall()

    def upsert_patient(self, patient_id: str, name: str, age: int = 0, gender: str = ""):
        self.execute(
            "INSERT OR IGNORE INTO patients (id, name, age, gender) VALUES (?, ?, ?, ?)",
            (patient_id, name, age, gender),
        )

    def create_session(self, session_id: str, patient_id: str, instruction: str):
        self.execute(
            "INSERT INTO sessions (id, patient_id, instruction) VALUES (?, ?, ?)",
            (session_id, patient_id, instruction),
        )

    def complete_session(self, session_id: str):
        self.execute(
            "UPDATE sessions SET status='completed', ended_at=CURRENT_TIMESTAMP WHERE id=?",
            (session_id,),
        )

    def save_report(self, report_id: str, session_id: str, report_json: str):
        self.execute(
            "INSERT INTO reports (id, session_id, report_json) VALUES (?, ?, ?)",
            (report_id, session_id, report_json),
        )

    def get_report(self, session_id: str):
        return self.fetchone(
            "SELECT report_json FROM reports WHERE session_id=?", (session_id,)
        )

    def get_patient_history(self, patient_id: str):
        return self.fetchall(
            """SELECT r.report_json, r.created_at
               FROM reports r JOIN sessions s ON r.session_id = s.id
               WHERE s.patient_id=? ORDER BY r.created_at DESC""",
            (patient_id,),
        )

    def get_all_reports(self, limit: int = 50):
        return self.fetchall(
            """SELECT r.report_json, r.created_at, s.patient_id, s.instruction
               FROM reports r JOIN sessions s ON r.session_id = s.id
               ORDER BY r.created_at DESC LIMIT ?""",
            (limit,),
        )

    def record_consent(self, patient_id: str, consent_type: str, expires_days: int = 90):
        from datetime import datetime, timedelta
        consent_id = str(uuid.uuid4())
        expires_at = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()
        self.execute(
            "INSERT INTO consents (id, patient_id, consent_type, expires_at) VALUES (?, ?, ?, ?)",
            (consent_id, patient_id, consent_type, expires_at),
        )

    def check_consent(self, patient_id: str, consent_type: str) -> bool:
        from datetime import datetime
        row = self.fetchone(
            """SELECT expires_at FROM consents
               WHERE patient_id=? AND consent_type=?
               ORDER BY granted_at DESC LIMIT 1""",
            (patient_id, consent_type),
        )
        if not row:
            return False
        try:
            expires_at = datetime.fromisoformat(row[0])
            return datetime.utcnow() < expires_at
        except (ValueError, TypeError):
            return False

    def purge_expired_data(self, days: int = 90):
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        self.execute(
            "DELETE FROM reports WHERE created_at < ?", (cutoff,),
        )
        self.execute(
            "DELETE FROM sessions WHERE ended_at IS NOT NULL AND ended_at < ?",
            (cutoff,),
        )

    def save_landmarks_batch(self, session_id: str, frames: list):
        """Bulk insert landmark frames (each: {frame_number, timestamp, landmarks_json})."""
        if not frames:
            return
        rows = [(session_id, f["frame_number"], f["timestamp"], f["landmarks_json"]) for f in frames]
        with self._lock:
            self._conn.executemany(
                "INSERT INTO raw_landmarks (session_id, frame_number, timestamp, landmarks_json) VALUES (?, ?, ?, ?)",
                rows,
            )
            self._conn.commit()

    def get_landmarks(self, session_id: str):
        """Retrieve all landmark frames for a session, ordered by frame_number."""
        return self.fetchall(
            "SELECT frame_number, timestamp, landmarks_json FROM raw_landmarks WHERE session_id=? ORDER BY frame_number",
            (session_id,),
        )

    def delete_landmarks(self, session_id: str):
        """Delete raw landmark data for a session."""
        self.execute("DELETE FROM raw_landmarks WHERE session_id=?", (session_id,))

    def get_stats(self) -> dict:
        total_patients = self.fetchone("SELECT COUNT(DISTINCT patient_id) FROM sessions")
        total_sessions = self.fetchone("SELECT COUNT(*) FROM sessions")
        completed = self.fetchone("SELECT COUNT(*) FROM sessions WHERE status='completed'")

        all_reports = self.fetchall("SELECT report_json FROM reports")
        referral = monitor = normal = rehab = 0
        for (rj,) in all_reports:
            try:
                data = json.loads(rj)
                instr = data.get("instruction", "")
                if instr.startswith("rehab_"):
                    rehab += 1
                    continue
                risks = data.get("risk_levels", {})
                if any(v == "referral" for v in risks.values()):
                    referral += 1
                elif any(v == "monitor" for v in risks.values()):
                    monitor += 1
                else:
                    normal += 1
            except (json.JSONDecodeError, AttributeError):
                continue

        return {
            "total_patients": total_patients[0] if total_patients else 0,
            "total_sessions": total_sessions[0] if total_sessions else 0,
            "completed_sessions": completed[0] if completed else 0,
            "risk_distribution": {"referral": referral, "monitor": monitor, "normal": normal},
            "rehab_sessions": rehab,
        }
