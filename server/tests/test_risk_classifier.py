import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core.risk_classifier import RiskClassifier, _frame_confidence
from core.clinical_thresholds import STROKE, PARKINSON, SARCOPENIA, CONFIDENCE
from models.schemas import RiskLevel


class TestClassifyStroke:

    def test_normal_low_values(self):
        risk, conf, detail = RiskClassifier.classify_stroke(
            mean_asi=0.02, angle_asymmetry=3.0, frame_count=100
        )
        assert risk == RiskLevel.NORMAL
        assert isinstance(conf, float)
        assert isinstance(detail, dict)
        assert "asi_score" in detail
        assert "angle_score" in detail
        assert "composite" in detail

    def test_monitor_asi_in_range(self):
        risk, conf, detail = RiskClassifier.classify_stroke(
            mean_asi=0.10, angle_asymmetry=3.0, frame_count=100
        )
        assert risk == RiskLevel.MONITOR

    def test_monitor_angle_in_range(self):
        risk, conf, detail = RiskClassifier.classify_stroke(
            mean_asi=0.0, angle_asymmetry=11.0, frame_count=100
        )
        assert risk == RiskLevel.MONITOR

    def test_referral_high_asi(self):
        risk, conf, detail = RiskClassifier.classify_stroke(
            mean_asi=0.20, angle_asymmetry=3.0, frame_count=100
        )
        assert risk == RiskLevel.REFERRAL

    def test_referral_high_angle(self):
        risk, conf, detail = RiskClassifier.classify_stroke(
            mean_asi=0.16, angle_asymmetry=5.0, frame_count=100
        )
        assert risk == RiskLevel.REFERRAL

    def test_referral_both_high(self):
        risk, conf, detail = RiskClassifier.classify_stroke(
            mean_asi=0.20, angle_asymmetry=15.0, frame_count=100
        )
        assert risk == RiskLevel.REFERRAL

    def test_zero_values(self):
        risk, conf, detail = RiskClassifier.classify_stroke(
            mean_asi=0.0, angle_asymmetry=0.0, frame_count=100
        )
        assert risk == RiskLevel.NORMAL
        composite = detail["composite"]
        assert composite == 0.0

    def test_very_high_values(self):
        risk, conf, detail = RiskClassifier.classify_stroke(
            mean_asi=1.0, angle_asymmetry=90.0, frame_count=100
        )
        assert risk == RiskLevel.REFERRAL

    def test_returns_tuple_of_three(self):
        result = RiskClassifier.classify_stroke(0.05, 3.0)
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_return_types(self):
        risk, conf, detail = RiskClassifier.classify_stroke(0.05, 3.0)
        assert isinstance(risk, RiskLevel)
        assert isinstance(conf, float)
        assert isinstance(detail, dict)

    def test_boundary_asi_normal_max(self):
        risk_just_below, _, _ = RiskClassifier.classify_stroke(
            mean_asi=STROKE.asi_normal_max - 0.001, angle_asymmetry=0.0, frame_count=100
        )
        risk_at, _, _ = RiskClassifier.classify_stroke(
            mean_asi=STROKE.asi_normal_max, angle_asymmetry=0.0, frame_count=100
        )
        assert risk_just_below == RiskLevel.NORMAL
        assert risk_at == RiskLevel.MONITOR or risk_at == RiskLevel.NORMAL

    def test_boundary_asi_monitor_max(self):
        risk_at_monitor, _, _ = RiskClassifier.classify_stroke(
            mean_asi=STROKE.asi_monitor_max, angle_asymmetry=0.0, frame_count=100
        )
        risk_above, _, _ = RiskClassifier.classify_stroke(
            mean_asi=STROKE.asi_monitor_max + 0.01, angle_asymmetry=10.0, frame_count=100
        )
        assert risk_above == RiskLevel.REFERRAL

    def test_frame_count_zero(self):
        risk, conf, detail = RiskClassifier.classify_stroke(
            mean_asi=0.05, angle_asymmetry=3.0, frame_count=0
        )
        assert risk == RiskLevel.NORMAL
        assert conf < 0.5


class TestClassifyParkinson:

    def test_normal_no_tremor_data(self):
        risk, conf, detail = RiskClassifier.classify_parkinson(
            dominant_freq=None, tremor_amplitude=None, tremor_pct=0.0, frame_count=100
        )
        assert risk == RiskLevel.NORMAL
        assert detail.get("reason") == "insufficient_data"

    def test_referral_parkinsonian_freq(self):
        risk, conf, detail = RiskClassifier.classify_parkinson(
            dominant_freq=5.0, tremor_amplitude=0.008, tremor_pct=0.40, frame_count=200
        )
        assert risk == RiskLevel.REFERRAL

    def test_monitor_moderate_tremor(self):
        risk, conf, detail = RiskClassifier.classify_parkinson(
            dominant_freq=5.0, tremor_amplitude=0.001, tremor_pct=0.10, frame_count=100
        )
        assert risk == RiskLevel.MONITOR

    def test_normal_outside_tremor_zone(self):
        risk, conf, detail = RiskClassifier.classify_parkinson(
            dominant_freq=1.0, tremor_amplitude=0.001, tremor_pct=0.05, frame_count=100
        )
        assert risk == RiskLevel.NORMAL

    def test_return_types(self):
        risk, conf, detail = RiskClassifier.classify_parkinson(
            dominant_freq=4.0, tremor_amplitude=0.003, tremor_pct=0.1, frame_count=100
        )
        assert isinstance(risk, RiskLevel)
        assert isinstance(conf, float)
        assert isinstance(detail, dict)

    def test_freq_in_postural_zone(self):
        risk, _, detail = RiskClassifier.classify_parkinson(
            dominant_freq=8.0, tremor_amplitude=0.005, tremor_pct=0.25, frame_count=100
        )
        assert detail["freq_score"] == 0.6

    def test_freq_in_broad_zone_atypical(self):
        risk, _, detail = RiskClassifier.classify_parkinson(
            dominant_freq=3.2, tremor_amplitude=0.001, tremor_pct=0.05, frame_count=100
        )
        assert detail["freq_score"] == 0.3

    def test_zero_amplitude(self):
        risk, conf, detail = RiskClassifier.classify_parkinson(
            dominant_freq=5.0, tremor_amplitude=0.0, tremor_pct=0.0, frame_count=100
        )
        assert isinstance(risk, RiskLevel)

    def test_none_amplitude(self):
        risk, conf, detail = RiskClassifier.classify_parkinson(
            dominant_freq=5.0, tremor_amplitude=None, tremor_pct=0.1, frame_count=100
        )
        assert isinstance(risk, RiskLevel)


class TestClassifySarcopenia:

    def test_normal_fast_transition(self):
        risk, conf, detail = RiskClassifier.classify_sarcopenia(
            transition_duration=2.0, age=30
        )
        assert risk == RiskLevel.NORMAL
        assert detail["age_group"] == "Muda (<60)"

    def test_monitor_moderate_transition(self):
        risk, conf, detail = RiskClassifier.classify_sarcopenia(
            transition_duration=3.5, age=30
        )
        assert risk == RiskLevel.MONITOR

    def test_referral_slow_transition(self):
        risk, conf, detail = RiskClassifier.classify_sarcopenia(
            transition_duration=5.0, age=30
        )
        assert risk == RiskLevel.REFERRAL

    def test_none_duration(self):
        risk, conf, detail = RiskClassifier.classify_sarcopenia(
            transition_duration=None, age=30
        )
        assert risk == RiskLevel.NORMAL
        assert detail.get("reason") == "no_transition_detected"

    def test_age_stratified_senior_60(self):
        risk, conf, detail = RiskClassifier.classify_sarcopenia(
            transition_duration=4.0, age=65
        )
        assert detail["age_group"] == "Senior (60-69)"

    def test_age_stratified_lansia_75(self):
        risk, conf, detail = RiskClassifier.classify_sarcopenia(
            transition_duration=4.0, age=75
        )
        assert detail["age_group"] == "Lansia (70-79)"

    def test_age_stratified_elderly_85(self):
        risk, conf, detail = RiskClassifier.classify_sarcopenia(
            transition_duration=5.0, age=85
        )
        assert detail["age_group"] == "Tua (≥80)"

    def test_none_age_uses_default(self):
        risk, conf, detail = RiskClassifier.classify_sarcopenia(
            transition_duration=4.0, age=None
        )
        assert detail["age_group"] == "Default"

    def test_return_types(self):
        risk, conf, detail = RiskClassifier.classify_sarcopenia(
            transition_duration=2.0, age=30
        )
        assert isinstance(risk, RiskLevel)
        assert isinstance(conf, float)
        assert isinstance(detail, dict)

    def test_confidence_is_high_for_sts(self):
        risk, conf, detail = RiskClassifier.classify_sarcopenia(
            transition_duration=2.0, age=30
        )
        assert conf == 0.85

    def test_senior_normal_threshold(self):
        risk_normal, _, _ = RiskClassifier.classify_sarcopenia(
            transition_duration=2.5, age=65
        )
        assert risk_normal == RiskLevel.NORMAL

    def test_senior_monitor_threshold(self):
        risk_monitor, _, _ = RiskClassifier.classify_sarcopenia(
            transition_duration=4.0, age=65
        )
        assert risk_monitor == RiskLevel.MONITOR


class TestFrameConfidence:

    def test_high_confidence(self):
        conf = _frame_confidence(CONFIDENCE.high_confidence_frames)
        assert conf == 0.95

    def test_zero_frames(self):
        conf = _frame_confidence(0)
        assert conf >= 0.1

    def test_low_frames(self):
        conf = _frame_confidence(10)
        assert 0.1 <= conf < 0.70

    def test_medium_frames(self):
        conf = _frame_confidence(CONFIDENCE.medium_confidence_frames)
        assert 0.70 <= conf < 0.95