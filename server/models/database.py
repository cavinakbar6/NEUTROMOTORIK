"""
Database — SQLite persistence untuk pasien, sesi, dan laporan.
Thread-safe dengan WAL mode dan indexes.
"""

import json
import sqlite3
import threading
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

        # Indexes for faster queries
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_patient ON sessions(patient_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_reports_session ON reports(session_id)")

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

    def get_stats(self) -> dict:
        total_patients = self.fetchone("SELECT COUNT(DISTINCT patient_id) FROM sessions")
        total_sessions = self.fetchone("SELECT COUNT(*) FROM sessions")
        completed = self.fetchone("SELECT COUNT(*) FROM sessions WHERE status='completed'")

        all_reports = self.fetchall("SELECT report_json FROM reports")
        referal = monitor = normal = 0
        for (rj,) in all_reports:
            try:
                data = json.loads(rj)
                risks = data.get("risk_levels", {})
                if any(v == "referal" for v in risks.values()):
                    referal += 1
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
            "risk_distribution": {"referal": referal, "monitor": monitor, "normal": normal},
        }
