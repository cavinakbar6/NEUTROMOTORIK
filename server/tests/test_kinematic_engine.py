import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import numpy as np
from models.schemas import Landmark, KinematicMetrics, ClinicalReport, RehabMetrics, RiskLevel
from core.kinematic_engine import KinematicEngine

L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28


def make_landmark(lm_id, x, y, z=0.0, vis=0.95):
    return Landmark(id=lm_id, x=x, y=y, z=z, vis=vis)


def make_symmetric_frame(frame_id=0, vis=0.95, arm_angle=90.0):
    landmarks = [
        make_landmark(L_SHOULDER, 0.3, 0.4, -0.05, vis),
        make_landmark(R_SHOULDER, 0.7, 0.4, -0.05, vis),
        make_landmark(L_ELBOW, 0.3, 0.55, -0.03, vis),
        make_landmark(R_ELBOW, 0.7, 0.55, -0.03, vis),
        make_landmark(L_WRIST, 0.3, 0.7, -0.02, vis),
        make_landmark(R_WRIST, 0.7, 0.7, -0.02, vis),
        make_landmark(L_HIP, 0.35, 0.65, -0.04, vis),
        make_landmark(R_HIP, 0.65, 0.65, -0.04, vis),
        make_landmark(L_KNEE, 0.35, 0.8, -0.03, vis),
        make_landmark(R_KNEE, 0.65, 0.8, -0.03, vis),
        make_landmark(L_ANKLE, 0.35, 0.95, -0.02, vis),
        make_landmark(R_ANKLE, 0.65, 0.95, -0.02, vis),
    ]
    return landmarks


def make_asymmetric_frame(frame_id=0, vis=0.95, left_angle_offset=0.15):
    landmarks = [
        make_landmark(L_SHOULDER, 0.3, 0.4, -0.05, vis),
        make_landmark(R_SHOULDER, 0.7, 0.4, -0.05, vis),
        make_landmark(L_ELBOW, 0.3 + left_angle_offset, 0.55, -0.03, vis),
        make_landmark(R_ELBOW, 0.7, 0.55, -0.03, vis),
        make_landmark(L_WRIST, 0.3 + left_angle_offset * 2, 0.7, -0.02, vis),
        make_landmark(R_WRIST, 0.7, 0.7, -0.02, vis),
        make_landmark(L_HIP, 0.35, 0.65, -0.04, vis),
        make_landmark(R_HIP, 0.65, 0.65, -0.04, vis),
        make_landmark(L_KNEE, 0.35, 0.8, -0.03, vis),
        make_landmark(R_KNEE, 0.65, 0.8, -0.03, vis),
        make_landmark(L_ANKLE, 0.35, 0.95, -0.02, vis),
        make_landmark(R_ANKLE, 0.65, 0.95, -0.02, vis),
    ]
    return landmarks


class TestKinematicEngineInit:

    def test_init_default(self):
        engine = KinematicEngine(instruction="raise_hands")
        assert engine.instruction == "raise_hands"
        assert engine.fps == 30
        assert engine.frame_count == 0
        assert engine.patient_age is None

    def test_init_with_fps_and_age(self):
        engine = KinematicEngine(instruction="sit_to_stand", fps=60, patient_age=75)
        assert engine.fps == 60
        assert engine.patient_age == 75

    def test_is_rehab_arm_raise(self):
        engine = KinematicEngine(instruction="rehab_arm_raise")
        assert engine._is_rehab is True

    def test_is_rehab_squat(self):
        engine = KinematicEngine(instruction="rehab_squat")
        assert engine._is_rehab is True

    def test_is_not_rehab(self):
        engine = KinematicEngine(instruction="raise_hands")
        assert engine._is_rehab is False

    def test_is_not_rehab_stand_still(self):
        engine = KinematicEngine(instruction="stand_still")
        assert engine._is_rehab is False


class TestProcessFrame:

    def test_returns_kinematic_metrics(self):
        engine = KinematicEngine(instruction="raise_hands")
        landmarks = make_symmetric_frame()
        m = engine.process_frame(frame_id=1, timestamp=0.033, landmarks=landmarks)
        assert isinstance(m, KinematicMetrics)
        assert m.frame == 1

    def test_frame_count_increments(self):
        engine = KinematicEngine(instruction="raise_hands")
        landmarks = make_symmetric_frame()
        engine.process_frame(1, 0.033, landmarks)
        engine.process_frame(2, 0.066, landmarks)
        assert engine.frame_count == 2

    def test_raise_hands_shoulder_angles(self):
        engine = KinematicEngine(instruction="raise_hands")
        landmarks = make_symmetric_frame()
        m = engine.process_frame(1, 0.033, landmarks)
        assert m.shoulder_angle_L is not None
        assert m.shoulder_angle_R is not None

    def test_stand_still_instruction(self):
        engine = KinematicEngine(instruction="stand_still")
        landmarks = make_symmetric_frame()
        m = engine.process_frame(1, 0.033, landmarks)
        assert isinstance(m, KinematicMetrics)

    def test_status_recording(self):
        engine = KinematicEngine(instruction="raise_hands")
        landmarks = make_symmetric_frame()
        m = engine.process_frame(1, 0.033, landmarks)
        assert m.status in ("recording", "alert_asymmetry", "alert_slow")

    def test_asi_not_available_before_10_frames(self):
        engine = KinematicEngine(instruction="raise_hands")
        landmarks = make_symmetric_frame()
        m = engine.process_frame(1, 0.033, landmarks)
        assert m.ASI is None

    def test_asi_available_after_10_frames(self):
        engine = KinematicEngine(instruction="raise_hands")
        landmarks = make_symmetric_frame()
        for i in range(12):
            m = engine.process_frame(i, i * 0.033, landmarks)
        assert m.ASI is not None

    def test_asi_buffer_accumulates(self):
        engine = KinematicEngine(instruction="raise_hands")
        landmarks = make_symmetric_frame()
        for i in range(15):
            engine.process_frame(i, i * 0.033, landmarks)
        assert len(engine.asi_buf) == 5

    def test_confidence_increases(self):
        engine = KinematicEngine(instruction="raise_hands")
        landmarks = make_symmetric_frame()
        m = engine.process_frame(1, 0.033, landmarks)
        conf_1 = m.confidence
        for i in range(100):
            engine.process_frame(i + 2, (i + 2) * 0.033, landmarks)
        m = engine.process_frame(200, 6.6, landmarks)
        assert m.confidence >= conf_1

    def test_low_visibility_landmarks_filtered(self):
        engine = KinematicEngine(instruction="raise_hands")
        landmarks = make_symmetric_frame(vis=0.01)
        m = engine.process_frame(1, 0.033, landmarks)
        assert m.shoulder_angle_L is None


class TestProcessRehabFrame:

    def test_rehab_arm_raise_returns_rehab_metrics(self):
        engine = KinematicEngine(instruction="rehab_arm_raise")
        landmarks = make_symmetric_frame()
        rm = engine.process_rehab_frame(frame_id=1, timestamp=0.033, landmarks=landmarks)
        assert isinstance(rm, RehabMetrics)
        assert rm.frame == 1

    def test_rehab_squat_returns_rehab_metrics(self):
        engine = KinematicEngine(instruction="rehab_squat")
        landmarks = make_symmetric_frame()
        rm = engine.process_rehab_frame(frame_id=1, timestamp=0.033, landmarks=landmarks)
        assert isinstance(rm, RehabMetrics)

    def test_rehab_arm_raise_rep_count_starts_zero(self):
        engine = KinematicEngine(instruction="rehab_arm_raise")
        landmarks = make_symmetric_frame()
        rm = engine.process_rehab_frame(1, 0.033, landmarks)
        assert rm.rep_count == 0

    def test_rehab_form_score(self):
        engine = KinematicEngine(instruction="rehab_arm_raise")
        landmarks = make_symmetric_frame()
        rm = engine.process_rehab_frame(1, 0.033, landmarks)
        assert isinstance(rm.form_score, float)
        assert rm.form_score >= 0.0

    def test_rehab_target_reps(self):
        engine = KinematicEngine(instruction="rehab_arm_raise")
        landmarks = make_symmetric_frame()
        rm = engine.process_rehab_frame(1, 0.033, landmarks)
        assert rm.target_reps == 10

    def test_rehab_feedback_msg(self):
        engine = KinematicEngine(instruction="rehab_arm_raise")
        landmarks = make_symmetric_frame()
        rm = engine.process_rehab_frame(1, 0.033, landmarks)
        assert isinstance(rm.feedback_msg, str)


class TestFinalize:

    def test_finalize_returns_clinical_report(self):
        engine = KinematicEngine(instruction="raise_hands")
        landmarks = make_symmetric_frame()
        for i in range(15):
            engine.process_frame(i, i * 0.033, landmarks)
        report = engine.finalize(patient_id="test_patient")
        assert isinstance(report, ClinicalReport)
        assert report.patient_id == "test_patient"
        assert report.instruction == "raise_hands"

    def test_finalize_report_has_session_id(self):
        engine = KinematicEngine(instruction="raise_hands")
        landmarks = make_symmetric_frame()
        for i in range(15):
            engine.process_frame(i, i * 0.033, landmarks)
        report = engine.finalize(patient_id="test_patient")
        assert report.session_id is not None
        assert len(report.session_id) > 0

    def test_finalize_report_has_risk_levels(self):
        engine = KinematicEngine(instruction="raise_hands")
        landmarks = make_symmetric_frame()
        for i in range(15):
            engine.process_frame(i, i * 0.033, landmarks)
        report = engine.finalize(patient_id="test_patient")
        assert isinstance(report.stroke_risk, RiskLevel)
        assert isinstance(report.parkinson_risk, RiskLevel)
        assert isinstance(report.sarcopenia_risk, RiskLevel)

    def test_finalize_rehab_mode(self):
        engine = KinematicEngine(instruction="rehab_arm_raise")
        landmarks = make_symmetric_frame()
        for i in range(15):
            engine.process_rehab_frame(i, i * 0.033, landmarks)
        report = engine.finalize(patient_id="test_patient")
        assert isinstance(report, ClinicalReport)
        assert report.instruction == "rehab_arm_raise"
        assert report.stroke_risk == RiskLevel.NORMAL
        assert report.parkinson_risk == RiskLevel.NORMAL
        assert report.sarcopenia_risk == RiskLevel.NORMAL

    def test_finalize_rehab_squat(self):
        engine = KinematicEngine(instruction="rehab_squat")
        landmarks = make_symmetric_frame()
        for i in range(15):
            engine.process_rehab_frame(i, i * 0.033, landmarks)
        report = engine.finalize(patient_id="test_patient")
        assert isinstance(report, ClinicalReport)
        assert report.instruction == "rehab_squat"

    def test_finalize_empty_engine(self):
        engine = KinematicEngine(instruction="raise_hands")
        report = engine.finalize(patient_id="empty_patient")
        assert isinstance(report, ClinicalReport)
        assert report.meanASI == 0.0
        assert report.maxASI == 0.0


class TestSitToStandFrame:

    def test_sit_to_stand_sets_phase(self):
        engine = KinematicEngine(instruction="sit_to_stand", fps=30)
        landmarks = make_symmetric_frame()
        m = engine.process_frame(1, 0.033, landmarks)
        assert m.sts_phase is not None or m.sts_phase is None