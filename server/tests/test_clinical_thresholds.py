import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from dataclasses import FrozenInstanceError
from core.clinical_thresholds import (
    StrokeThresholds, ParkinsonThresholds, STSAgeGroup,
    SarcopeniaThresholds, ConfidenceParams,
    STROKE, PARKINSON, SARCOPENIA, CONFIDENCE,
)


class TestStrokeThresholds:

    def test_asi_normal_max(self):
        assert STROKE.asi_normal_max == 0.08

    def test_asi_monitor_max(self):
        assert STROKE.asi_monitor_max == 0.15

    def test_angle_normal_max(self):
        assert STROKE.angle_normal_max == 6.0

    def test_angle_monitor_max(self):
        assert STROKE.angle_monitor_max == 12.0

    def test_weights_sum_to_one(self):
        total = STROKE.weight_asi + STROKE.weight_angle
        assert abs(total - 1.0) < 1e-9

    def test_asi_thresholds_ordering(self):
        assert STROKE.asi_normal_max < STROKE.asi_monitor_max

    def test_angle_thresholds_ordering(self):
        assert STROKE.angle_normal_max < STROKE.angle_monitor_max

    def test_min_frames_positive(self):
        assert STROKE.min_frames > 0

    def test_frozen(self):
        with pytest.raises(FrozenInstanceError):
            STROKE.asi_normal_max = 0.20


class TestParkinsonThresholds:

    def test_park_freq_range(self):
        assert PARKINSON.park_freq_min == 3.5
        assert PARKINSON.park_freq_max == 7.0

    def test_postural_freq_range(self):
        assert PARKINSON.postural_freq_min == 5.0
        assert PARKINSON.postural_freq_max == 12.0

    def test_search_freq_range(self):
        assert PARKINSON.search_freq_min == 3.0
        assert PARKINSON.search_freq_max == 15.0

    def test_amplitude_thresholds(self):
        assert PARKINSON.amp_normal_max == 0.003
        assert PARKINSON.amp_monitor_max == 0.006

    def test_pct_thresholds(self):
        assert PARKINSON.pct_normal_max == 0.15
        assert PARKINSON.pct_monitor_max == 0.35

    def test_weights_sum_approximately_one(self):
        total = PARKINSON.weight_freq + PARKINSON.weight_amp + PARKINSON.weight_pct
        assert abs(total - 1.0) < 1e-9

    def test_thresholds_ordering(self):
        assert PARKINSON.amp_normal_max < PARKINSON.amp_monitor_max
        assert PARKINSON.pct_normal_max < PARKINSON.pct_monitor_max
        assert PARKINSON.park_freq_min < PARKINSON.park_freq_max

    def test_min_seconds_positive(self):
        assert PARKINSON.min_seconds > 0

    def test_frozen(self):
        with pytest.raises(FrozenInstanceError):
            PARKINSON.park_freq_min = 1.0


class TestSarcopeniaThresholds:

    def test_age_groups_count(self):
        assert len(SARCOPENIA.age_groups) == 4

    def test_young_group(self):
        g = SARCOPENIA.age_groups[0]
        assert g.label == "Muda (<60)"
        assert g.age_min == 0
        assert g.age_max == 59
        assert g.normal_max_s == 2.5
        assert g.monitor_max_s == 4.0

    def test_senior_60_group(self):
        g = SARCOPENIA.age_groups[1]
        assert g.label == "Senior (60-69)"
        assert g.age_min == 60
        assert g.age_max == 69
        assert g.normal_max_s == 3.0
        assert g.monitor_max_s == 5.0

    def test_lansia_70_group(self):
        g = SARCOPENIA.age_groups[2]
        assert g.label == "Lansia (70-79)"
        assert g.age_min == 70
        assert g.age_max == 79
        assert g.normal_max_s == 3.5
        assert g.monitor_max_s == 6.0

    def test_elderly_80_group(self):
        g = SARCOPENIA.age_groups[3]
        assert g.label == "Tua (≥80)"
        assert g.age_min == 80
        assert g.age_max == 120

    def test_get_thresholds_young_age(self):
        g = SARCOPENIA.get_thresholds(25)
        assert g.label == "Muda (<60)"
        assert g.normal_max_s == 2.5

    def test_get_thresholds_senior(self):
        g = SARCOPENIA.get_thresholds(65)
        assert g.label == "Senior (60-69)"

    def test_get_thresholds_lansia(self):
        g = SARCOPENIA.get_thresholds(75)
        assert g.label == "Lansia (70-79)"

    def test_get_thresholds_elderly(self):
        g = SARCOPENIA.get_thresholds(85)
        assert g.label == "Tua (≥80)"

    def test_get_thresholds_none_returns_default(self):
        g = SARCOPENIA.get_thresholds(None)
        assert g.label == "Default"
        assert g.normal_max_s == SARCOPENIA.default_normal_max
        assert g.monitor_max_s == SARCOPENIA.default_monitor_max

    def test_get_thresholds_default_values(self):
        assert SARCOPENIA.default_normal_max == 3.0
        assert SARCOPENIA.default_monitor_max == 5.0

    def test_movement_thresholds(self):
        assert SARCOPENIA.movement_threshold > 0
        assert SARCOPENIA.stable_threshold > 0
        assert SARCOPENIA.stable_frames_required > 0

    def test_movement_threshold_greater_than_stable(self):
        assert SARCOPENIA.movement_threshold > SARCOPENIA.stable_threshold

    def test_frozen(self):
        with pytest.raises(FrozenInstanceError):
            SARCOPENIA.default_normal_max = 99.0

    def test_age_group_frozen(self):
        with pytest.raises(FrozenInstanceError):
            SARCOPENIA.age_groups[0].label = "modified"


class TestConfidenceParams:

    def test_exists(self):
        assert CONFIDENCE is not None

    def test_min_visibility(self):
        assert 0 < CONFIDENCE.min_visibility <= 1.0

    def test_frame_thresholds_ordering(self):
        assert CONFIDENCE.low_confidence_frames < CONFIDENCE.medium_confidence_frames
        assert CONFIDENCE.medium_confidence_frames < CONFIDENCE.high_confidence_frames

    def test_visibility_thresholds_ordering(self):
        assert CONFIDENCE.good_visibility < CONFIDENCE.excellent_visibility

    def test_reasonable_values(self):
        assert CONFIDENCE.high_confidence_frames >= 300
        assert CONFIDENCE.low_confidence_frames >= 10

    def test_frozen(self):
        with pytest.raises(FrozenInstanceError):
            CONFIDENCE.min_visibility = 0.99