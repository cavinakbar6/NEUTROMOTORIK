import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from models.schemas import ClinicalReport, RiskLevel
from core.session_manager import SessionManager


class TestSessionManagerCreate:

    @patch("core.session_manager.Database")
    def test_create_returns_session_id(self, mock_db_cls):
        mock_instance = MagicMock()
        mock_db_cls.return_value = mock_instance
        mock_db_cls._instance = None

        sm = SessionManager()
        sid = sm.create(patient_id="patient1", instruction="raise_hands")
        assert isinstance(sid, str)
        assert len(sid) > 0

    @patch("core.session_manager.Database")
    def test_create_stores_in_active(self, mock_db_cls):
        mock_instance = MagicMock()
        mock_db_cls.return_value = mock_instance
        mock_db_cls._instance = None

        sm = SessionManager()
        sid = sm.create(patient_id="patient1", instruction="raise_hands")
        assert sid in sm.active
        assert sm.active[sid]["patient_id"] == "patient1"
        assert sm.active[sid]["instruction"] == "raise_hands"

    @patch("core.session_manager.Database")
    def test_create_with_age(self, mock_db_cls):
        mock_instance = MagicMock()
        mock_db_cls.return_value = mock_instance
        mock_db_cls._instance = None

        sm = SessionManager()
        sid = sm.create(patient_id="p1", instruction="sit_to_stand", age=75)
        assert sm.active[sid]["age"] == 75

    @patch("core.session_manager.Database")
    def test_create_calls_db(self, mock_db_cls):
        mock_instance = MagicMock()
        mock_db_cls.return_value = mock_instance
        mock_db_cls._instance = None

        sm = SessionManager()
        sid = sm.create(patient_id="patient1", instruction="raise_hands")
        mock_instance.create_session.assert_called_once_with(sid, "patient1", "raise_hands")


class TestSessionManagerGetSessionInfo:

    @patch("core.session_manager.Database")
    def test_get_session_info_existing(self, mock_db_cls):
        mock_instance = MagicMock()
        mock_db_cls.return_value = mock_instance
        mock_db_cls._instance = None

        sm = SessionManager()
        sid = sm.create(patient_id="patient1", instruction="raise_hands")
        info = sm.get_session_info(sid)
        assert info is not None
        assert info["patient_id"] == "patient1"

    @patch("core.session_manager.Database")
    def test_get_session_info_nonexistent(self, mock_db_cls):
        mock_instance = MagicMock()
        mock_db_cls.return_value = mock_instance
        mock_db_cls._instance = None

        sm = SessionManager()
        info = sm.get_session_info("nonexistent_id")
        assert info is None


class TestSessionManagerSaveReport:

    @patch("core.session_manager.ReportGenerator")
    @patch("core.session_manager.Database")
    def test_save_report_calls_db(self, mock_db_cls, mock_rg_cls):
        mock_db_instance = MagicMock()
        mock_db_cls.return_value = mock_db_instance
        mock_db_cls._instance = None

        mock_rg_cls.to_dict.return_value = {
            "report_id": "r1",
            "patient_id": "p1",
            "risk_levels": {"stroke": "normal", "parkinson": "normal", "sarcopenia": "normal"},
        }

        sm = SessionManager()
        sid = sm.create(patient_id="p1", instruction="raise_hands")

        report = ClinicalReport(
            session_id="report-uuid",
            patient_id="p1",
            timestamp=datetime.now(),
            instruction="raise_hands",
        )

        result = sm.save_report(report, sid)

        mock_db_instance.upsert_patient.assert_called_once_with("p1", "p1")
        mock_db_instance.complete_session.assert_called_once_with(sid)
        assert isinstance(result, dict)
        assert "report_id" in result

    @patch("core.session_manager.ReportGenerator")
    @patch("core.session_manager.Database")
    def test_save_report_removes_from_active(self, mock_db_cls, mock_rg_cls):
        mock_db_instance = MagicMock()
        mock_db_cls.return_value = mock_db_instance
        mock_db_cls._instance = None

        mock_rg_cls.to_dict.return_value = {
            "report_id": "r1",
            "patient_id": "p1",
            "risk_levels": {"stroke": "normal"},
        }

        sm = SessionManager()
        sid = sm.create(patient_id="p1", instruction="raise_hands")
        assert sid in sm.active

        report = ClinicalReport(
            session_id="report-uuid",
            patient_id="p1",
            timestamp=datetime.now(),
            instruction="raise_hands",
        )

        sm.save_report(report, sid)
        assert sid not in sm.active


class TestSessionManagerActiveCount:

    @patch("core.session_manager.Database")
    def test_active_count_zero(self, mock_db_cls):
        mock_instance = MagicMock()
        mock_db_cls.return_value = mock_instance
        mock_db_cls._instance = None

        sm = SessionManager()
        assert sm.get_active_count() == 0

    @patch("core.session_manager.Database")
    def test_active_count_after_create(self, mock_db_cls):
        mock_instance = MagicMock()
        mock_db_cls.return_value = mock_instance
        mock_db_cls._instance = None

        sm = SessionManager()
        sm.create(patient_id="p1", instruction="raise_hands")
        sm.create(patient_id="p2", instruction="stand_still")
        assert sm.get_active_count() == 2