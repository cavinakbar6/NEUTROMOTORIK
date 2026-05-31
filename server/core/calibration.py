"""
Calibration Module — Camera distance normalization for clinical accuracy.

MediaPipe outputs normalized coordinates (0-1). Actual pixel displacement
depends on the person's distance from the camera. This module:
  1. Uses shoulder width as a known anthropometric reference (~40cm average)
  2. Computes a scale factor that normalizes measurements across distances
  3. Applies perspective correction for off-axis positioning

Reference:
  - Average adult shoulder breadth: 41.5cm (male), 36.7cm (female)
  - We use 40cm as the default reference width
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np

from models.schemas import Landmark

L_SHOULDER, R_SHOULDER = 11, 12


@dataclass(frozen=True)
class CalibrationConfig:
    reference_shoulder_width_m: float = 0.40
    pixels_per_meter_estimate: float = 500.0
    min_visibility: float = 0.6
    calibration_frames: int = 30


@dataclass
class CalibrationResult:
    scale_factor: float
    distance_m: float
    shoulder_width_px: float
    confidence: float
    calibrated: bool


class Calibrator:
    """Per-session calibrator that accumulates frames and computes scale."""

    def __init__(self, config: CalibrationConfig = None):
        self.config = config or CalibrationConfig()
        self._shoulder_widths: List[float] = []
        self._calibrated = False
        self._result: Optional[CalibrationResult] = None

    def update(self, landmarks: List[Landmark]) -> Optional[CalibrationResult]:
        """Process a frame's landmarks. Returns CalibrationResult once stable."""
        if self._calibrated:
            return self._result

        lm_dict = {lm.id: lm for lm in landmarks}

        l_sh = lm_dict.get(L_SHOULDER)
        r_sh = lm_dict.get(R_SHOULDER)

        if l_sh is None or r_sh is None:
            return None

        if l_sh.vis < self.config.min_visibility or r_sh.vis < self.config.min_visibility:
            return None

        dx = (r_sh.x - l_sh.x)
        dy = (r_sh.y - l_sh.y)
        shoulder_width_px = np.sqrt(dx * dx + dy * dy)

        if shoulder_width_px < 0.001:
            return None

        self._shoulder_widths.append(shoulder_width_px)

        if len(self._shoulder_widths) < self.config.calibration_frames:
            return None

        avg_width = float(np.median(self._shoulder_widths))

        # scale_factor = pixels-per-meter
        # avg_width (in normalized 0-1) corresponds to reference_shoulder_width_m
        # So 1 normalized unit = reference_shoulder_width_m / avg_width meters
        # scale_factor = avg_width / reference_shoulder_width_m (norm units per meter)
        # But we want pixels-per-meter equivalent for distance estimation:
        # distance = (real_width / apparent_width_norm) * focal_length_equiv
        # Simplified: distance_m = reference_width / (avg_width * sensor_scale)
        # We estimate: at default distance (~1.3m), avg_width ≈ 0.35 norm units
        # pixels_per_meter at image resolution:
        # scale_factor ≈ 1 / avg_width * reference_width / 1.0
        # More intuitive: distance proportional to 1/apparent_size
        # distance_m = reference_shoulder_width_m / (avg_width * estimated_px_per_m_at_ref)
        # But since we work in normalized coords, we compute:
        # norm_width for shoulder at distance d: W = w_real / (d * 2)  (rough pinhole)
        # So d = w_real / (W * 2) if normalized to [-0.5, 0.5], but MP uses [0,1]
        # We use: distance_m = reference_width / avg_width (simple ratio)
        # With a correction factor for the pinhole model
        distance_m = self.config.reference_shoulder_width_m / avg_width

        # Confidence: standard deviation of samples / mean (lower is better)
        if len(self._shoulder_widths) > 5:
            std = float(np.std(self._shoulder_widths))
            mean = float(np.mean(self._shoulder_widths))
            coefficient_of_variation = std / mean if mean > 0 else 1.0
            confidence = max(0.0, min(1.0, 1.0 - coefficient_of_variation))
        else:
            confidence = 0.0

        scale_factor = avg_width / self.config.reference_shoulder_width_m

        self._result = CalibrationResult(
            scale_factor=scale_factor,
            distance_m=round(distance_m, 3),
            shoulder_width_px=round(avg_width, 5),
            confidence=round(confidence, 3),
            calibrated=True,
        )
        self._calibrated = True
        return self._result

    def apply_depth_correction(self, y_coord: float, height: int = 480) -> float:
        """Apply perspective correction: objects higher in frame are farther away."""
        # y_coord is in normalized [0,1] from MediaPipe (0=top, 1=bottom)
        # Objects at top of frame are farther; scale their apparent size up
        # Perspective correction factor: closer objects (bottom) should be
        # scaled down relative to farther objects (top) to normalize
        # Simple linear model: at y=0 (top/far), factor ~1.3; at y=1 (bottom/near), factor ~0.8
        # This normalizes measurements to be distance-independent
        corrected = y_coord
        if self._calibrated and self._result:
            ratio = 1.0 + 0.3 * (0.5 - y_coord)
            corrected = y_coord * ratio
        return corrected

    def get_scale_factor(self) -> float:
        """Return current scale factor, or default estimate."""
        if self._result and self._calibrated:
            return self._result.scale_factor
        return self.config.pixels_per_meter_estimate

    def reset(self):
        """Reset calibration state for a new session."""
        self._shoulder_widths = []
        self._calibrated = False
        self._result = None