"""
RiskClassifier — Multi-factor risk classification berdasarkan clinical thresholds.

Menggunakan weighted scoring system untuk mengklasifikasi risiko:
  1. Stroke: ASI + angle asymmetry → weighted risk score
  2. Parkinson: frequency zone + amplitude + duration → weighted risk score
  3. Sarcopenia: age-stratified transition duration
"""

from typing import Optional, Dict, Tuple
from models.schemas import RiskLevel
from core.clinical_thresholds import STROKE, PARKINSON, SARCOPENIA, CONFIDENCE


class RiskClassifier:
    """Multi-factor risk classifier dengan confidence scoring."""

    # ── Stroke Risk ─────────────────────────────────────────

    @staticmethod
    def classify_stroke(
        mean_asi: float,
        angle_asymmetry: float,
        frame_count: int = 0,
    ) -> Tuple[RiskLevel, float, Dict]:
        """
        Classify stroke risk berdasarkan ASI dan angle asymmetry.

        Returns: (risk_level, confidence, detail_dict)
        """
        # Compute sub-scores (0.0 = normal, 0.5 = monitor, 1.0 = referal)
        if mean_asi > STROKE.asi_monitor_max:
            asi_score = 1.0
        elif mean_asi > STROKE.asi_normal_max:
            # Linear interpolation dalam zona monitor
            asi_score = 0.5 + 0.5 * (
                (mean_asi - STROKE.asi_normal_max)
                / (STROKE.asi_monitor_max - STROKE.asi_normal_max)
            )
        else:
            asi_score = mean_asi / STROKE.asi_normal_max * 0.5 if STROKE.asi_normal_max > 0 else 0.0

        if angle_asymmetry > STROKE.angle_monitor_max:
            angle_score = 1.0
        elif angle_asymmetry > STROKE.angle_normal_max:
            angle_score = 0.5 + 0.5 * (
                (angle_asymmetry - STROKE.angle_normal_max)
                / (STROKE.angle_monitor_max - STROKE.angle_normal_max)
            )
        else:
            angle_score = (angle_asymmetry / STROKE.angle_normal_max * 0.5
                          if STROKE.angle_normal_max > 0 else 0.0)

        # Weighted composite score
        composite = (
            asi_score * STROKE.weight_asi
            + angle_score * STROKE.weight_angle
        )

        # Classify
        if composite >= 0.7:
            risk = RiskLevel.REFERAL
        elif composite >= 0.35:
            risk = RiskLevel.MONITOR
        else:
            risk = RiskLevel.NORMAL

        # Confidence based on data quantity
        confidence = _frame_confidence(frame_count)

        detail = {
            "asi_score": round(asi_score, 3),
            "angle_score": round(angle_score, 3),
            "composite": round(composite, 3),
            "confidence": round(confidence, 2),
        }

        return risk, confidence, detail

    # ── Parkinson Risk ──────────────────────────────────────

    @staticmethod
    def classify_parkinson(
        dominant_freq: Optional[float],
        tremor_amplitude: Optional[float],
        tremor_pct: float,
        frame_count: int = 0,
    ) -> Tuple[RiskLevel, float, Dict]:
        """
        Classify Parkinson risk berdasarkan tremor characteristics.

        Returns: (risk_level, confidence, detail_dict)
        """
        if dominant_freq is None:
            return RiskLevel.NORMAL, 0.5, {"reason": "insufficient_data"}

        # 1. Frequency zone score
        if PARKINSON.park_freq_min <= dominant_freq <= PARKINSON.park_freq_max:
            freq_score = 1.0  # In parkinsonian rest tremor zone
        elif PARKINSON.postural_freq_min <= dominant_freq <= PARKINSON.postural_freq_max:
            freq_score = 0.6  # In postural tremor zone
        elif PARKINSON.search_freq_min <= dominant_freq <= PARKINSON.search_freq_max:
            freq_score = 0.3  # In broad tremor zone but atypical
        else:
            freq_score = 0.0  # Outside tremor zone

        # 2. Amplitude score
        amp = tremor_amplitude or 0.0
        if amp > PARKINSON.amp_monitor_max:
            amp_score = 1.0
        elif amp > PARKINSON.amp_normal_max:
            amp_score = 0.5 + 0.5 * (
                (amp - PARKINSON.amp_normal_max)
                / (PARKINSON.amp_monitor_max - PARKINSON.amp_normal_max)
            )
        else:
            amp_score = amp / PARKINSON.amp_normal_max * 0.5 if PARKINSON.amp_normal_max > 0 else 0.0

        # 3. Duration percentage score
        if tremor_pct > PARKINSON.pct_monitor_max:
            pct_score = 1.0
        elif tremor_pct > PARKINSON.pct_normal_max:
            pct_score = 0.5 + 0.5 * (
                (tremor_pct - PARKINSON.pct_normal_max)
                / (PARKINSON.pct_monitor_max - PARKINSON.pct_normal_max)
            )
        else:
            pct_score = tremor_pct / PARKINSON.pct_normal_max * 0.5 if PARKINSON.pct_normal_max > 0 else 0.0

        # Weighted composite
        composite = (
            freq_score * PARKINSON.weight_freq
            + amp_score * PARKINSON.weight_amp
            + pct_score * PARKINSON.weight_pct
        )

        # Classify
        if composite >= 0.65:
            risk = RiskLevel.REFERAL
        elif composite >= 0.30:
            risk = RiskLevel.MONITOR
        else:
            risk = RiskLevel.NORMAL

        confidence = _frame_confidence(frame_count)

        detail = {
            "freq_score": round(freq_score, 3),
            "amp_score": round(amp_score, 3),
            "pct_score": round(pct_score, 3),
            "composite": round(composite, 3),
            "confidence": round(confidence, 2),
        }

        return risk, confidence, detail

    # ── Sarcopenia Risk ─────────────────────────────────────

    @staticmethod
    def classify_sarcopenia(
        transition_duration: Optional[float],
        age: Optional[int] = None,
    ) -> Tuple[RiskLevel, float, Dict]:
        """
        Classify sarcopenia risk berdasarkan STS duration (age-stratified).

        Returns: (risk_level, confidence, detail_dict)
        """
        if transition_duration is None:
            return RiskLevel.NORMAL, 0.5, {"reason": "no_transition_detected"}

        group = SARCOPENIA.get_thresholds(age)

        if transition_duration > group.monitor_max_s:
            risk = RiskLevel.REFERAL
        elif transition_duration > group.normal_max_s:
            risk = RiskLevel.MONITOR
        else:
            risk = RiskLevel.NORMAL

        # Confidence is high for STS since it's a direct measurement
        confidence = 0.85

        detail = {
            "age_group": group.label,
            "normal_max": group.normal_max_s,
            "monitor_max": group.monitor_max_s,
            "duration": round(transition_duration, 2),
            "confidence": round(confidence, 2),
        }

        return risk, confidence, detail


# ── Helper ──────────────────────────────────────────────────

def _frame_confidence(frame_count: int) -> float:
    """Compute confidence level based on number of analyzed frames."""
    if frame_count >= CONFIDENCE.high_confidence_frames:
        return 0.95
    elif frame_count >= CONFIDENCE.medium_confidence_frames:
        return 0.70 + 0.25 * (
            (frame_count - CONFIDENCE.medium_confidence_frames)
            / (CONFIDENCE.high_confidence_frames - CONFIDENCE.medium_confidence_frames)
        )
    elif frame_count >= CONFIDENCE.low_confidence_frames:
        return 0.40 + 0.30 * (
            (frame_count - CONFIDENCE.low_confidence_frames)
            / (CONFIDENCE.medium_confidence_frames - CONFIDENCE.low_confidence_frames)
        )
    else:
        return max(0.1, frame_count / CONFIDENCE.low_confidence_frames * 0.40)
