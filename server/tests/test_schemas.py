import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from datetime import datetime
from models.schemas import (
    Landmark, RiskLevel, InstructionType,
    KinematicMetrics, ClinicalReport, RehabMetrics,
    SessionStartMsg, LandmarksMsg, SessionEndMsg,
    AckMsg, HeartbeatMsg, HeartbeatAck, WSErrorMessage,
)


class TestLandmark:

    def test_creation(self):
        lm = Landmark(id=0, x=0.5, y=0.5, z=-0.1, vis=0.99)
        assert lm.id == 0
        assert lm.x == 0.5
        assert lm.y == 0.5
        assert lm.z == -0.1
        assert lm.vis == 0.99

    def test_default_visibility(self):
        lm = Landmark(id=0, x=0.5, y=0.5, z=-0.1)
        assert lm.vis == 0.0

    def test_visibility_range(self):
        lm = Landmark(id=0, x=0.5, y=0.5, z=-0.1, vis=1.0)
        assert lm.vis == 1.0

    def test_visibility_zero(self):
        lm = Landmark(id=0, x=0.5, y=0.5, z=-0.1, vis=0.0)
        assert lm.vis == 0.0

    def test_invalid_visibility_too_high(self):
        with pytest.raises(Exception):
            Landmark(id=0, x=0.5, y=0.5, z=-0.1, vis=1.5)

    def test_invalid_visibility_negative(self):
        with pytest.raises(Exception):
            Landmark(id=0, x=0.5, y=0.5, z=-0.1, vis=-0.1)

    def test_required_fields(self):
        with pytest.raises(Exception):
            Landmark(x=0.5, y=0.5, z=-0.1)


class TestRiskLevel:

    def test_normal_value(self):
        assert RiskLevel.NORMAL.value == "normal"

    def test_monitor_value(self):
        assert RiskLevel.MONITOR.value == "monitor"

    def test_referral_value(self):
        assert RiskLevel.REFERRAL.value == "referral"

    def test_all_values(self):
        values = {level.value for level in RiskLevel}
        assert values == {"normal", "monitor", "referral"}

    def test_comparison(self):
        assert RiskLevel.NORMAL != RiskLevel.MONITOR
        assert RiskLevel.MONITOR != RiskLevel.REFERRAL

    def test_is_string_enum(self):
        assert isinstance(RiskLevel.NORMAL, str)


class TestInstructionType:

    def test_raise_hands(self):
        assert InstructionType.RAISE_HANDS.value == "raise_hands"

    def test_stand_still(self):
        assert InstructionType.STAND_STILL.value == "stand_still"

    def test_sit_to_stand(self):
        assert InstructionType.SIT_TO_STAND.value == "sit_to_stand"

    def test_rehab_arm_raise(self):
        assert InstructionType.REHAB_ARM_RAISE.value == "rehab_arm_raise"

    def test_rehab_squat(self):
        assert InstructionType.REHAB_SQUAT.value == "rehab_squat"


class TestKinematicMetrics:

    def test_defaults(self):
        m = KinematicMetrics(frame=1)
        assert m.frame == 1
        assert m.type == "metrics"
        assert m.shoulder_angle_L is None
        assert m.shoulder_angle_R is None
        assert m.elbow_angle_L is None
        assert m.elbow_angle_R is None
        assert m.ASI is None
        assert m.dominant_freq_hz is None
        assert m.tremor_amplitude is None
        assert m.sts_phase is None
        assert m.sts_duration is None
        assert m.psd_freqs is None
        assert m.psd_power is None
        assert m.confidence is None
        assert m.status == "recording"

    def test_with_values(self):
        m = KinematicMetrics(
            frame=42,
            shoulder_angle_L=90.0,
            shoulder_angle_R=92.0,
            ASI=0.05,
            confidence=0.85,
        )
        assert m.frame == 42
        assert m.shoulder_angle_L == 90.0
        assert m.ASI == 0.05


class TestClinicalReport:

    def test_creation_minimal(self):
        r = ClinicalReport(
            session_id="abc123",
            patient_id="patient1",
            timestamp=datetime.now(),
            instruction="raise_hands",
        )
        assert r.session_id == "abc123"
        assert r.patient_id == "patient1"
        assert r.instruction == "raise_hands"
        assert r.meanASI == 0.0
        assert r.maxASI == 0.0
        assert r.stroke_risk == RiskLevel.NORMAL
        assert r.parkinson_risk == RiskLevel.NORMAL
        assert r.sarcopenia_risk == RiskLevel.NORMAL

    def test_with_risk_levels(self):
        r = ClinicalReport(
            session_id="abc123",
            patient_id="patient1",
            timestamp=datetime.now(),
            instruction="stand_still",
            stroke_risk=RiskLevel.REFERRAL,
            parkinson_risk=RiskLevel.MONITOR,
            sarcopenia_risk=RiskLevel.NORMAL,
        )
        assert r.stroke_risk == RiskLevel.REFERRAL
        assert r.parkinson_risk == RiskLevel.MONITOR
        assert r.sarcopenia_risk == RiskLevel.NORMAL

    def test_optional_fields(self):
        r = ClinicalReport(
            session_id="abc123",
            patient_id="patient1",
            timestamp=datetime.now(),
            instruction="sit_to_stand",
        )
        assert r.dominant_freq is None
        assert r.tremor_amplitude is None
        assert r.transition_duration is None
        assert r.transition_velocity is None
        assert r.ai_narrative is None


class TestRehabMetrics:

    def test_defaults(self):
        rm = RehabMetrics(frame=1)
        assert rm.frame == 1
        assert rm.type == "rehab_metrics"
        assert rm.rep_count == 0
        assert rm.form_score == 0.0
        assert rm.feedback_msg == ""
        assert rm.phase is None
        assert rm.target_reps == 10

    def test_with_values(self):
        rm = RehabMetrics(
            frame=5,
            rep_count=3,
            form_score=75.5,
            feedback_msg="Bagus!",
            phase="up",
            target_reps=10,
        )
        assert rm.rep_count == 3
        assert rm.form_score == 75.5
        assert rm.feedback_msg == "Bagus!"
        assert rm.phase == "up"


class TestSessionStartMsg:

    def test_creation(self):
        msg = SessionStartMsg(patient_id="p1", instruction=InstructionType.RAISE_HANDS)
        assert msg.type == "session_start"
        assert msg.patient_id == "p1"
        assert msg.instruction == InstructionType.RAISE_HANDS


class TestLandmarksMsg:

    def test_creation(self):
        lm = [Landmark(id=0, x=0.5, y=0.5, z=-0.1, vis=0.9)]
        msg = LandmarksMsg(frame=1, timestamp=1.0, landmarks=lm)
        assert msg.type == "landmarks"
        assert len(msg.landmarks) == 1


class TestSessionEndMsg:

    def test_creation(self):
        msg = SessionEndMsg(session_id="abc")
        assert msg.type == "session_end"
        assert msg.session_id == "abc"


class TestHeartbeatMsg:

    def test_creation(self):
        msg = HeartbeatMsg()
        assert msg.type == "heartbeat"


class TestWSErrorMessage:

    def test_creation(self):
        msg = WSErrorMessage(message="test error")
        assert msg.type == "error"
        assert msg.message == "test error"