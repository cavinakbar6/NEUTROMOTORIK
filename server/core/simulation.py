"""
Simulation Engine — Generate realistic landmark sequences without a camera.

For demo, testing, and competition presentation when a webcam is unavailable.
Produces synthetic MediaPipe landmarks that simulate:
  - Normal symmetric movement
  - Asymmetric movement (stroke indicator)
  - Tremor patterns (Parkinson indicator)
  - Sit-to-stand transitions (Sarcopenia indicator)
  - Rehab arm raise / squat patterns
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from models.schemas import Landmark


@dataclass
class SimulationConfig:
    instruction: str = "raise_hands"
    fps: int = 30
    duration_s: float = 15.0
    patient_age: int = 65
    scenario: str = "normal"
    noise_level: float = 0.002


# MediaPipe Pose landmark indices
NOSE = 0
L_EYE_INNER, L_EYE, L_EYE_OUTER = 1, 2, 3
R_EYE_INNER, R_EYE, R_EYE_OUTER = 4, 5, 6
L_EAR, R_EAR = 7, 8
MOUTH_L, MOUTH_R = 9, 10
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_PINKY, R_PINKY = 17, 18
L_INDEX, R_INDEX = 19, 20
L_THUMB, R_THUMB = 21, 22
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28
L_HEEL, R_HEEL = 29, 30
L_FOOT_IDX, R_FOOT_IDX = 31, 32


class SimulationEngine:
    """Generate synthetic landmark data for demo/testing."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self._frame = 0
        self._total_frames = int(config.fps * config.duration_s)

    def generate_frame(self) -> Optional[Tuple[int, float, List[Landmark]]]:
        """Generate next frame. Returns (frame_number, timestamp, landmarks) or None if done."""
        if self._frame >= self._total_frames:
            return None

        t = self._frame / self.config.fps
        landmarks = self._generate_landmarks(t)
        result = (self._frame, t, landmarks)
        self._frame += 1
        return result

    def generate_all(self) -> List[Tuple[int, float, List[Landmark]]]:
        """Generate all frames at once."""
        frames = []
        while True:
            f = self.generate_frame()
            if f is None:
                break
            frames.append(f)
        return frames

    def _generate_landmarks(self, t: float) -> List[Landmark]:
        base = self._base_pose(t)

        instruction = self.config.instruction
        if instruction == "raise_hands":
            base = self._apply_raise_hands(t, base)
        elif instruction == "stand_still":
            base = self._apply_stand_still(t, base)
        elif instruction == "sit_to_stand":
            base = self._apply_sit_to_stand(t, base)
        elif instruction == "rehab_arm_raise":
            base = self._apply_rehab_arm_raise(t, base)
        elif instruction == "rehab_squat":
            base = self._apply_rehab_squat(t, base)

        scenario = self.config.scenario
        if scenario == "stroke_mild":
            base = self._add_asymmetry(base, "left", 0.08)
        elif scenario == "stroke_severe":
            base = self._add_asymmetry(base, "left", 0.18)
        elif scenario == "parkinson_tremor":
            base = self._add_tremor(base, 5.0, 0.008, [L_WRIST, R_WRIST, L_ELBOW, R_ELBOW])
        elif scenario == "sarcopenia_slow":
            pass  # Slower STS animations are handled in _apply_sit_to_stand

        for lm in base:
            lm.x += random.gauss(0, self.config.noise_level)
            lm.y += random.gauss(0, self.config.noise_level)
            lm.z += random.gauss(0, self.config.noise_level)
            lm.vis = max(0.0, min(1.0, lm.vis + random.gauss(0, 0.01)))

        return base

    def _base_pose(self, t: float) -> List[Landmark]:
        """Standing pose, arms at sides."""
        landmarks = [None] * 33

        # Head
        landmarks[NOSE] = Landmark(id=0, x=0.5, y=0.12, z=0.0, vis=0.99)
        landmarks[L_EYE_INNER] = Landmark(id=1, x=0.47, y=0.10, z=0.02, vis=0.95)
        landmarks[L_EYE] = Landmark(id=2, x=0.46, y=0.10, z=0.02, vis=0.95)
        landmarks[L_EYE_OUTER] = Landmark(id=3, x=0.44, y=0.10, z=0.02, vis=0.90)
        landmarks[R_EYE_INNER] = Landmark(id=4, x=0.53, y=0.10, z=0.02, vis=0.95)
        landmarks[R_EYE] = Landmark(id=5, x=0.54, y=0.10, z=0.02, vis=0.95)
        landmarks[R_EYE_OUTER] = Landmark(id=6, x=0.56, y=0.10, z=0.02, vis=0.90)
        landmarks[L_EAR] = Landmark(id=7, x=0.42, y=0.11, z=0.05, vis=0.80)
        landmarks[R_EAR] = Landmark(id=8, x=0.58, y=0.11, z=0.05, vis=0.80)
        landmarks[MOUTH_L] = Landmark(id=9, x=0.48, y=0.14, z=0.02, vis=0.90)
        landmarks[MOUTH_R] = Landmark(id=10, x=0.52, y=0.14, z=0.02, vis=0.90)

        # Shoulders
        landmarks[L_SHOULDER] = Landmark(id=11, x=0.38, y=0.28, z=0.02, vis=0.98)
        landmarks[R_SHOULDER] = Landmark(id=12, x=0.62, y=0.28, z=0.02, vis=0.98)

        # Arms at sides — elbows below shoulders, wrists below elbows
        landmarks[L_ELBOW] = Landmark(id=13, x=0.34, y=0.43, z=0.04, vis=0.95)
        landmarks[R_ELBOW] = Landmark(id=14, x=0.66, y=0.43, z=0.04, vis=0.95)
        landmarks[L_WRIST] = Landmark(id=15, x=0.33, y=0.56, z=0.04, vis=0.92)
        landmarks[R_WRIST] = Landmark(id=16, x=0.67, y=0.56, z=0.04, vis=0.92)

        # Hands
        landmarks[L_PINKY] = Landmark(id=17, x=0.32, y=0.58, z=0.04, vis=0.85)
        landmarks[R_PINKY] = Landmark(id=18, x=0.68, y=0.58, z=0.04, vis=0.85)
        landmarks[L_INDEX] = Landmark(id=19, x=0.325, y=0.57, z=0.04, vis=0.85)
        landmarks[R_INDEX] = Landmark(id=20, x=0.675, y=0.57, z=0.04, vis=0.85)
        landmarks[L_THUMB] = Landmark(id=21, x=0.335, y=0.55, z=0.03, vis=0.80)
        landmarks[R_THUMB] = Landmark(id=22, x=0.665, y=0.55, z=0.03, vis=0.80)

        # Hips
        landmarks[L_HIP] = Landmark(id=23, x=0.42, y=0.56, z=0.02, vis=0.97)
        landmarks[R_HIP] = Landmark(id=24, x=0.58, y=0.56, z=0.02, vis=0.97)

        # Knees
        landmarks[L_KNEE] = Landmark(id=25, x=0.43, y=0.73, z=0.03, vis=0.95)
        landmarks[R_KNEE] = Landmark(id=26, x=0.57, y=0.73, z=0.03, vis=0.95)

        # Ankles
        landmarks[L_ANKLE] = Landmark(id=27, x=0.43, y=0.90, z=0.03, vis=0.93)
        landmarks[R_ANKLE] = Landmark(id=28, x=0.57, y=0.90, z=0.03, vis=0.93)

        # Heels
        landmarks[L_HEEL] = Landmark(id=29, x=0.42, y=0.91, z=0.03, vis=0.85)
        landmarks[R_HEEL] = Landmark(id=30, x=0.58, y=0.91, z=0.03, vis=0.85)

        # Foot index (toe)
        landmarks[L_FOOT_IDX] = Landmark(id=31, x=0.44, y=0.92, z=0.02, vis=0.75)
        landmarks[R_FOOT_IDX] = Landmark(id=32, x=0.56, y=0.92, z=0.02, vis=0.75)

        return landmarks

    def _lerp(self, a: float, b: float, t_frac: float) -> float:
        """Linear interpolation."""
        return a + (b - a) * max(0.0, min(1.0, t_frac))

    def _smooth(self, t: float, t_start: float, t_end: float) -> float:
        """Smooth step: 0 → 1 over [t_start, t_end] with ease-in-out."""
        if t <= t_start:
            return 0.0
        if t >= t_end:
            return 1.0
        x = (t - t_start) / (t_end - t_start)
        return x * x * (3.0 - 2.0 * x)

    def _apply_raise_hands(self, t: float, base: List[Landmark]) -> List[Landmark]:
        """Animate both arms raising, with scenario adjustments."""
        dur = self.config.duration_s
        raise_start = 0.5
        lower_start = dur * 0.65
        lower_end = dur * 0.9

        if t < raise_start:
            frac = 0.0
        elif t < raise_start + 1.5:
            frac = self._smooth(t, raise_start, raise_start + 1.5)
        elif t < lower_start:
            frac = 1.0
        else:
            frac = 1.0 - self._smooth(t, lower_start, lower_end)

        # Shoulder angle: ~30° at rest → ~160° at full raise
        # Elbow moves up and out; wrist moves up further
        base[L_ELBOW] = Landmark(
            id=13,
            x=self._lerp(0.34, 0.30, frac),
            y=self._lerp(0.43, 0.18, frac),
            z=self._lerp(0.04, -0.08, frac),
            vis=0.95,
        )
        base[R_ELBOW] = Landmark(
            id=14,
            x=self._lerp(0.66, 0.70, frac),
            y=self._lerp(0.43, 0.18, frac),
            z=self._lerp(0.04, -0.08, frac),
            vis=0.95,
        )
        base[L_WRIST] = Landmark(
            id=15,
            x=self._lerp(0.33, 0.28, frac),
            y=self._lerp(0.56, 0.06, frac),
            z=self._lerp(0.04, -0.10, frac),
            vis=0.92,
        )
        base[R_WRIST] = Landmark(
            id=16,
            x=self._lerp(0.67, 0.72, frac),
            y=self._lerp(0.56, 0.06, frac),
            z=self._lerp(0.04, -0.10, frac),
            vis=0.92,
        )
        # Update hands to follow wrist
        for idx, ox, oy in [(L_PINKY, -0.01, 0.02), (R_PINKY, 0.01, 0.02),
                             (L_INDEX, -0.005, 0.01), (R_INDEX, 0.005, 0.01),
                             (L_THUMB, 0.01, -0.01), (R_THUMB, -0.01, -0.01)]:
            base[idx] = Landmark(
                id=idx,
                x=base[L_WRIST if idx < 17 else R_WRIST].x + ox
                if idx in (17, 19, 21) else base[R_WRIST].x + ox,
                y=base[L_WRIST if idx < 17 else R_WRIST].y + oy
                if idx in (17, 19, 21) else base[R_WRIST].y + oy,
                z=base[L_WRIST if idx < 17 else R_WRIST].z + 0.01
                if idx in (17, 19, 21) else base[R_WRIST].z + 0.01,
                vis=0.85,
            )

        # Slow STS transition for sarcopenia
        if self.config.scenario == "sarcopenia_slow":
            base = self._add_tremor(base, 5.0, 0.003, [L_WRIST, R_WRIST])

        return base

    def _apply_stand_still(self, t: float, base: List[Landmark]) -> List[Landmark]:
        """Static standing with potential tremor."""
        # Slight natural sway
        sway_x = 0.002 * math.sin(2 * math.pi * 0.15 * t)
        for i in range(33):
            if base[i] is not None:
                base[i] = Landmark(
                    id=base[i].id,
                    x=base[i].x + sway_x,
                    y=base[i].y,
                    z=base[i].z,
                    vis=base[i].vis,
                )
        return base

    def _apply_sit_to_stand(self, t: float, base: List[Landmark]) -> List[Landmark]:
        """Animate sit-to-stand transition."""
        dur = self.config.duration_s
        # Sitting phase → transition → standing
        sit_end = dur * 0.2
        trans_start = sit_end
        trans_speed = 0.6 if self.config.scenario != "sarcopenia_slow" else 1.4
        trans_end = trans_start + trans_speed
        stand_start = trans_end

        if t < sit_end:
            frac = 0.0  # sitting
        elif t < stand_start:
            frac = self._smooth(t, trans_start, trans_end)
        else:
            frac = 1.0  # standing

        # Sitting: hip y ≈ 0.72, knee y ≈ 0.72 (bent), shoulder y ≈ 0.42
        # Standing: hip y ≈ 0.56, knee y ≈ 0.73, shoulder y ≈ 0.28
        # Interpolate body landmarks
        body_parts = {
            NOSE: (0.50, 0.30, 0.50, 0.12),
            L_SHOULDER: (0.38, 0.45, 0.38, 0.28),
            R_SHOULDER: (0.62, 0.45, 0.62, 0.28),
            L_ELBOW: (0.34, 0.58, 0.34, 0.43),
            R_ELBOW: (0.66, 0.58, 0.66, 0.43),
            L_WRIST: (0.33, 0.68, 0.33, 0.56),
            R_WRIST: (0.67, 0.68, 0.67, 0.56),
            L_HIP: (0.42, 0.72, 0.42, 0.56),
            R_HIP: (0.58, 0.72, 0.58, 0.56),
            L_KNEE: (0.38, 0.78, 0.43, 0.73),
            R_KNEE: (0.62, 0.78, 0.57, 0.73),
            L_ANKLE: (0.38, 0.90, 0.43, 0.90),
            R_ANKLE: (0.62, 0.90, 0.57, 0.90),
        }
        # (sit_x, sit_y, stand_x, stand_y) → lerp by frac
        for idx, (sx, sy, stx, sty) in body_parts.items():
            base[idx] = Landmark(
                id=idx,
                x=self._lerp(sx, stx, frac),
                y=self._lerp(sy, sty, frac),
                z=base[idx].z if base[idx] else 0.02,
                vis=base[idx].vis if base[idx] else 0.95,
            )

        # Update hand positions to match wrist
        for idx, wrist_idx, ox, oy in [
            (L_PINKY, L_WRIST, -0.01, 0.02), (R_PINKY, R_WRIST, 0.01, 0.02),
            (L_INDEX, L_WRIST, -0.005, 0.01), (R_INDEX, R_WRIST, 0.005, 0.01),
            (L_THUMB, L_WRIST, 0.01, -0.01), (R_THUMB, R_WRIST, -0.01, -0.01),
        ]:
            base[idx] = Landmark(
                id=idx,
                x=base[wrist_idx].x + ox,
                y=base[wrist_idx].y + oy,
                z=base[wrist_idx].z + 0.01,
                vis=0.85,
            )

        return base

    def _apply_rehab_arm_raise(self, t: float, base: List[Landmark]) -> List[Landmark]:
        """Animate arm raise exercise with rep counting."""
        # Rep cycle: 2s up, 0.5s hold, 2s down, 0.5s rest = 5s per rep
        cycle_duration = 4.0
        cycle_pos = (t % cycle_duration) / cycle_duration

        if cycle_pos < 0.4:
            # Raising phase (0 to ~2s)
            frac = self._smooth(t % cycle_duration, 0.0, cycle_duration * 0.4)
        elif cycle_pos < 0.5:
            # Hold at top
            frac = 1.0
        elif cycle_pos < 0.85:
            # Lowering phase
            lower_t = (cycle_pos - 0.5) * cycle_duration
            frac = 1.0 - self._smooth(lower_t, 0.0, cycle_duration * 0.35)
        else:
            # Brief rest
            frac = 0.0

        base[L_ELBOW] = Landmark(
            id=13,
            x=self._lerp(0.34, 0.30, frac),
            y=self._lerp(0.43, 0.18, frac),
            z=self._lerp(0.04, -0.08, frac),
            vis=0.95,
        )
        base[R_ELBOW] = Landmark(
            id=14,
            x=self._lerp(0.66, 0.70, frac),
            y=self._lerp(0.43, 0.18, frac),
            z=self._lerp(0.04, -0.08, frac),
            vis=0.95,
        )
        base[L_WRIST] = Landmark(
            id=15,
            x=self._lerp(0.33, 0.28, frac),
            y=self._lerp(0.56, 0.06, frac),
            z=self._lerp(0.04, -0.10, frac),
            vis=0.92,
        )
        base[R_WRIST] = Landmark(
            id=16,
            x=self._lerp(0.67, 0.72, frac),
            y=self._lerp(0.56, 0.06, frac),
            z=self._lerp(0.04, -0.10, frac),
            vis=0.92,
        )
        # Update hands
        for idx, wrist_idx, ox, oy in [
            (L_PINKY, L_WRIST, -0.01, 0.02), (R_PINKY, R_WRIST, 0.01, 0.02),
            (L_INDEX, L_WRIST, -0.005, 0.01), (R_INDEX, R_WRIST, 0.005, 0.01),
            (L_THUMB, L_WRIST, 0.01, -0.01), (R_THUMB, R_WRIST, -0.01, -0.01),
        ]:
            base[idx] = Landmark(
                id=idx,
                x=base[wrist_idx].x + ox,
                y=base[wrist_idx].y + oy,
                z=base[wrist_idx].z + 0.01,
                vis=0.85,
            )

        return base

    def _apply_rehab_squat(self, t: float, base: List[Landmark]) -> List[Landmark]:
        """Animate squat exercise with rep counting."""
        cycle_duration = 5.0
        cycle_pos = (t % cycle_duration) / cycle_duration

        if cycle_pos < 0.35:
            frac = self._smooth(t % cycle_duration, 0.0, cycle_duration * 0.35)
        elif cycle_pos < 0.45:
            # Hold at bottom
            frac = 1.0
        elif cycle_pos < 0.8:
            lower_t = (cycle_pos - 0.45) * cycle_duration
            frac = 1.0 - self._smooth(lower_t, 0.0, cycle_duration * 0.35)
        else:
            # Brief rest standing
            frac = 0.0

        # 0 = standing, 1 = deep squat
        body_parts = {
            NOSE: (0.50, 0.12, 0.50, 0.30),
            L_SHOULDER: (0.38, 0.28, 0.38, 0.45),
            R_SHOULDER: (0.62, 0.28, 0.62, 0.45),
            L_ELBOW: (0.34, 0.43, 0.34, 0.55),
            R_ELBOW: (0.66, 0.43, 0.66, 0.55),
            L_WRIST: (0.33, 0.56, 0.33, 0.62),
            R_WRIST: (0.67, 0.56, 0.67, 0.62),
            L_HIP: (0.42, 0.56, 0.42, 0.68),
            R_HIP: (0.58, 0.56, 0.58, 0.68),
            L_KNEE: (0.43, 0.73, 0.38, 0.76),
            R_KNEE: (0.57, 0.73, 0.62, 0.76),
            L_ANKLE: (0.43, 0.90, 0.43, 0.90),
            R_ANKLE: (0.57, 0.90, 0.57, 0.90),
        }
        for idx, (stx, sty, sqx, sqy) in body_parts.items():
            base[idx] = Landmark(
                id=idx,
                x=self._lerp(stx, sqx, frac),
                y=self._lerp(sty, sqy, frac),
                z=0.02,
                vis=0.95,
            )

        for idx, wrist_idx, ox, oy in [
            (L_PINKY, L_WRIST, -0.01, 0.02), (R_PINKY, R_WRIST, 0.01, 0.02),
            (L_INDEX, L_WRIST, -0.005, 0.01), (R_INDEX, R_WRIST, 0.005, 0.01),
            (L_THUMB, L_WRIST, 0.01, -0.01), (R_THUMB, R_WRIST, -0.01, -0.01),
        ]:
            base[idx] = Landmark(
                id=idx,
                x=base[wrist_idx].x + ox,
                y=base[wrist_idx].y + oy,
                z=base[wrist_idx].z + 0.01,
                vis=0.85,
            )

        return base

    def _add_tremor(self, landmarks: List[Landmark], freq_hz: float,
                    amplitude: float, joint_indices: List[int]) -> List[Landmark]:
        """Add sinusoidal tremor to specific joints."""
        t = self._frame / self.config.fps
        # Multiple harmonics for realistic tremor
        primary = amplitude * math.sin(2 * math.pi * freq_hz * t)
        harmonic = amplitude * 0.3 * math.sin(2 * math.pi * freq_hz * 2 * t + 0.5)
        phase_var = amplitude * 0.15 * math.sin(2 * math.pi * freq_hz * 3 * t + 1.2)
        tremor_y = primary + harmonic + phase_var

        for idx in joint_indices:
            if idx < len(landmarks) and landmarks[idx] is not None:
                landmarks[idx] = Landmark(
                    id=landmarks[idx].id,
                    x=landmarks[idx].x,
                    y=landmarks[idx].y + tremor_y,
                    z=landmarks[idx].z,
                    vis=landmarks[idx].vis,
                )
            # Also add smaller x-axis tremor
            if idx < 17:  # left side
                adj_idx = idx + 2  # next joint in chain
            else:
                adj_idx = idx + 2
            if adj_idx < 33 and landmarks[adj_idx] is not None:
                landmarks[adj_idx] = Landmark(
                    id=landmarks[adj_idx].id,
                    x=landmarks[adj_idx].x,
                    y=landmarks[adj_idx].y + tremor_y * 0.4,
                    z=landmarks[adj_idx].z,
                    vis=landmarks[adj_idx].vis,
                )
        return landmarks

    def _add_asymmetry(self, landmarks: List[Landmark], side: str,
                       angle_offset: float) -> List[Landmark]:
        """Add angle asymmetry to one side of the body.

        side: 'left' affects left arm (indices < 17 but >= 11)
        angle_offset: roughly equivalent to ASI value
        """
        if side == "left":
            # Raise left arm slightly less → lower angle on left side
            for idx in [L_SHOULDER, L_ELBOW, L_WRIST, L_PINKY, L_INDEX, L_THUMB]:
                if landmarks[idx] is not None:
                    # Push left arm slightly down and inward
                    x_shift = -0.02 * angle_offset
                    y_shift = 0.04 * angle_offset
                    landmarks[idx] = Landmark(
                        id=landmarks[idx].id,
                        x=landmarks[idx].x + x_shift,
                        y=landmarks[idx].y + y_shift,
                        z=landmarks[idx].z,
                        vis=landmarks[idx].vis,
                    )
        else:
            # Affect right side
            for idx in [R_SHOULDER, R_ELBOW, R_WRIST, R_PINKY, R_INDEX, R_THUMB]:
                if landmarks[idx] is not None:
                    x_shift = 0.02 * angle_offset
                    y_shift = 0.04 * angle_offset
                    landmarks[idx] = Landmark(
                        id=landmarks[idx].id,
                        x=landmarks[idx].x + x_shift,
                        y=landmarks[idx].y + y_shift,
                        z=landmarks[idx].z,
                        vis=landmarks[idx].vis,
                    )
        return landmarks