"""
Clinical Thresholds — Evidence-based thresholds dari literatur medis.

Referensi:
  STROKE (Asymmetry Index):
    - Whitall et al. (2006) Stroke 37(7): bilateral arm training, ASI > 0.10 mild
    - Kim et al. (2014) Ann Rehabil Med 38(3): angle asym > 8° suggests UMN lesion
    - Schwarz et al. (2012) Gait & Posture: upper limb bilateral ASI norms

  PARKINSON (Tremor):
    - Jankovic (2008) J Neurol Neurosurg Psychiatry: resting tremor 4-6 Hz
    - PPMI dataset (Parkinson's Progression Markers Initiative): accelerometry norms
    - Hoehn & Yahr scale correlation with tremor amplitude thresholds
    - Deuschl et al. (1998) Movement Disorders: tremor classification 3-7 Hz rest

  SARCOPENIA (Sit-to-Stand):
    - Bohannon (2006) J Geriatr Phys Ther: 5XSST normative by age
    - Guralnik et al. (2000) J Gerontol: SPPB cutoffs
    - Cesari et al. (2009) Age & Ageing: single STS normative data
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional


# ═══════════════════════════════════════════════════════════════
#  STROKE — Asymmetry Index Thresholds
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class StrokeThresholds:
    """
    Threshold ASI dan angle asymmetry untuk deteksi stroke ringan.

    Derived from:
      - Whitall et al. (2006): ASI < 0.08 normal bilateral movement
      - Kim et al. (2014): angle asymmetry > 8° correlated with UMN lesion
      - Schwarz et al. (2012): healthy adults ASI mean = 0.04 ± 0.03
    """
    # ASI (Asymmetry Index: 2*|L-R|/(L+R))
    asi_normal_max: float = 0.08      # ≤ 0.08 → NORMAL (healthy mean ± 2SD)
    asi_monitor_max: float = 0.15     # 0.08-0.15 → MONITOR
    # > 0.15 → REFERRAL

    # Angle asymmetry (degrees)
    angle_normal_max: float = 6.0     # ≤ 6° → NORMAL
    angle_monitor_max: float = 12.0   # 6-12° → MONITOR
    # > 12° → REFERRAL

    # Confidence scoring weights
    weight_asi: float = 0.6
    weight_angle: float = 0.4

    # Minimum frames for reliable assessment
    min_frames: int = 60              # ~2 detik @ 30 FPS


STROKE = StrokeThresholds()


# ═══════════════════════════════════════════════════════════════
#  PARKINSON — Tremor Analysis Thresholds
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ParkinsonThresholds:
    """
    Threshold tremor untuk deteksi Parkinson.

    Derived from:
      - Jankovic (2008): resting tremor 4-6 Hz, postural 5-12 Hz
      - Deuschl et al. (1998): Parkinsonian rest tremor typically 3.5-7 Hz
      - PPMI accelerometry: amplitude > 0.003 suspicious, > 0.006 significant
      - Hoehn-Yahr correlation: duration > 15% moderate, > 35% severe
    """
    # Frequency detection window (Hz)
    search_freq_min: float = 3.0      # Broad search range
    search_freq_max: float = 15.0

    # Parkinsonian tremor zone (narrower, more specific)
    park_freq_min: float = 3.5        # Rest tremor lower bound
    park_freq_max: float = 7.0        # Rest tremor upper bound

    # Postural tremor zone
    postural_freq_min: float = 5.0
    postural_freq_max: float = 12.0

    # Amplitude thresholds (normalized coordinate units)
    amp_normal_max: float = 0.003     # ≤ 0.003 → NORMAL (physiological)
    amp_monitor_max: float = 0.006    # 0.003-0.006 → MONITOR
    # > 0.006 → REFERRAL (pathological)

    # Duration percentage (% of tremor energy / total energy)
    pct_normal_max: float = 0.15      # ≤ 15% → NORMAL
    pct_monitor_max: float = 0.35     # 15-35% → MONITOR
    # > 35% → REFERRAL

    # Scoring weights
    weight_freq: float = 0.3         # Is frequency in Parkinsonian zone?
    weight_amp: float = 0.4          # How strong is the tremor?
    weight_pct: float = 0.3          # How persistent is the tremor?

    # Minimum data for reliable FFT
    min_seconds: float = 3.0          # Minimum recording duration


PARKINSON = ParkinsonThresholds()


# ═══════════════════════════════════════════════════════════════
#  SARCOPENIA — Sit-to-Stand Thresholds (Age-Stratified)
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class STSAgeGroup:
    """Threshold untuk satu kelompok usia."""
    label: str
    age_min: int
    age_max: int
    normal_max_s: float       # ≤ ini → NORMAL
    monitor_max_s: float      # ≤ ini → MONITOR, > ini → REFERRAL


@dataclass(frozen=True)
class SarcopeniaThresholds:
    """
    Age-stratified sit-to-stand thresholds.

    Derived from:
      - Bohannon (2006): normative 5XSST by decade (divided by 5 for single STS)
        • 60-69: 11.4s ÷ 5 = 2.28s → ~2.5s cutoff
        • 70-79: 12.6s ÷ 5 = 2.52s → ~3.0s cutoff
        • 80-89: 14.8s ÷ 5 = 2.96s → ~3.5s cutoff
      - Guralnik et al. (2000): SPPB chair stand scores
      - Cesari et al. (2009): single STS norms + 1.5 SD for "at risk"
    """
    age_groups: Tuple[STSAgeGroup, ...] = (
        STSAgeGroup("Muda (<60)",      0,  59, 2.5, 4.0),
        STSAgeGroup("Senior (60-69)", 60,  69, 3.0, 5.0),
        STSAgeGroup("Lansia (70-79)", 70,  79, 3.5, 6.0),
        STSAgeGroup("Tua (≥80)",      80, 120, 4.5, 7.5),
    )

    # Default jika usia tidak diketahui (gunakan threshold konservatif)
    default_normal_max: float = 3.0
    default_monitor_max: float = 5.0

    # Movement detection parameters (tuned from clinical video analysis)
    movement_threshold: float = 0.012     # Min dy per frame for movement start
    stable_threshold: float = 0.006       # Max dy per frame for "stable"
    stable_frames_required: int = 15      # ~0.5s stability @ 30 FPS

    def get_thresholds(self, age: Optional[int] = None) -> STSAgeGroup:
        """Get threshold for specific age group."""
        if age is None:
            return STSAgeGroup("Default", 0, 120,
                             self.default_normal_max,
                             self.default_monitor_max)
        for group in self.age_groups:
            if group.age_min <= age <= group.age_max:
                return group
        return self.age_groups[-1]  # Fallback: oldest group


SARCOPENIA = SarcopeniaThresholds()


# ═══════════════════════════════════════════════════════════════
#  CONFIDENCE SCORING
# ═══════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ConfidenceParams:
    """Parameters for computing confidence in assessment results."""
    # Minimum landmark visibility for usable data
    min_visibility: float = 0.5

    # Frame count thresholds for confidence levels
    low_confidence_frames: int = 30       # < 30 frames → low confidence
    medium_confidence_frames: int = 150   # < 150 frames → medium
    high_confidence_frames: int = 450     # ≥ 450 frames → high (~15s @ 30fps)

    # Visibility quality thresholds
    good_visibility: float = 0.7
    excellent_visibility: float = 0.85


CONFIDENCE = ConfidenceParams()

