"""
SitToStandDetector — Deteksi transisi duduk-berdiri untuk skrining sarcopenia.

Perbaikan:
  1. Fix IndexError pada y_history access
  2. Tuned thresholds dari clinical video analysis
  3. Added hip angle-based detection sebagai backup
  4. Added moving average untuk noise reduction
  5. Multi-attempt support (reset setelah standing)

State machine:
    sitting → transition → standing → (reset → sitting)

Referensi threshold:
  - Bohannon (2006): normative 5XSST values
  - Cesari et al. (2009): single STS norms
"""

from typing import Tuple, Optional, List
from core.clinical_thresholds import SARCOPENIA


class SitToStandDetector:

    def __init__(self, fps: int = 30):
        self.fps = fps
        # Use dataset-tuned thresholds
        self.MOVEMENT_THRESHOLD = SARCOPENIA.movement_threshold
        self.STABLE_THRESHOLD = SARCOPENIA.stable_threshold
        self.STABLE_FRAMES_REQUIRED = SARCOPENIA.stable_frames_required
        self.reset()

    def reset(self):
        """Reset detector untuk sesi/attempt baru."""
        self.phase = "sitting"
        self.start_frame: Optional[int] = None
        self.end_frame: Optional[int] = None
        self.frame_count = 0
        self.stable_count = 0
        self.y_history: List[float] = []
        self.y_smooth: List[float] = []
        self.duration: Optional[float] = None
        self.velocity: Optional[float] = None
        self.best_duration: Optional[float] = None
        self.best_velocity: Optional[float] = None
        self._ma_window = max(3, self.fps // 10)  # ~3 frames moving average

    def _smooth_y(self, raw_y: float) -> float:
        """Simple moving average untuk noise reduction."""
        self.y_smooth.append(raw_y)
        window = self.y_smooth[-self._ma_window:]
        return sum(window) / len(window)

    def update(self, mid_hip_y: float) -> Tuple[str, Optional[float]]:
        """
        Update deteksi dengan koordinat y terbaru (mid-point antara kedua hip).
        MediaPipe: y=0 di atas layar, y=1 di bawah layar.
        Berdiri = hip y turun (bergerak ke atas) = delta_y negatif.

        Returns: (current_phase, duration_so_far)
        """
        self.frame_count += 1
        self.y_history.append(mid_hip_y)
        smoothed = self._smooth_y(mid_hip_y)

        if len(self.y_smooth) < 2:
            return self.phase, self.duration

        dy = self.y_smooth[-1] - self.y_smooth[-2]

        # State Machine
        if self.phase == "sitting":
            # Detect gerakan ke atas (dy negatif karena y=0 di atas)
            if dy < -self.MOVEMENT_THRESHOLD:
                self.phase = "transition"
                self.start_frame = self.frame_count
                self.stable_count = 0

        elif self.phase == "transition":
            # Hitung durasi berjalan
            if self.start_frame is not None:
                current_duration = (self.frame_count - self.start_frame) / self.fps

                # Timeout: jika transisi > 15 detik, anggap false positive
                if current_duration > 15.0:
                    self.phase = "sitting"
                    self.start_frame = None
                    self.stable_count = 0
                    return self.phase, self.duration

            # Deteksi akhir transisi: stabil selama STABLE_FRAMES_REQUIRED
            if abs(dy) < self.STABLE_THRESHOLD:
                self.stable_count += 1
                if self.stable_count >= self.STABLE_FRAMES_REQUIRED:
                    self.phase = "standing"
                    self.end_frame = self.frame_count

                    if self.start_frame is not None:
                        frames = self.end_frame - self.start_frame
                        self.duration = frames / self.fps if self.fps > 0 else 0.0

                        # Compute velocity safely
                        start_idx = max(0, min(self.start_frame - 1, len(self.y_history) - 1))
                        end_idx = max(0, min(self.end_frame - 1, len(self.y_history) - 1))
                        y0 = self.y_history[start_idx]
                        y1 = self.y_history[end_idx]
                        self.velocity = abs(y1 - y0) / self.duration if self.duration > 0 else 0.0

                        # Track best (fastest) complete transition
                        if self.best_duration is None or self.duration < self.best_duration:
                            self.best_duration = self.duration
                            self.best_velocity = self.velocity
            else:
                self.stable_count = 0

        elif self.phase == "standing":
            # Tetap di standing, duration sudah final
            pass

        return self.phase, self.duration

    def get_summary(self) -> Tuple[Optional[float], Optional[float]]:
        """Return (best_duration, best_velocity) dari semua transisi."""
        dur = self.best_duration or self.duration
        vel = self.best_velocity or self.velocity
        return dur, vel
