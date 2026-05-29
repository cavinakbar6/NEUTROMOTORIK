"""
KinematicEngine — Mesin komputasi utama per-sesi.
Menerima stream landmark, menghasilkan metrik kinematika real-time.

Perbaikan:
  - ASI: match angle_L dan angle_R per-frame (bukan terakhir saja)
  - PSD: Hitung Welch PSD secara incremental setiap N frame
  - Thresholds: gunakan clinical_thresholds + risk_classifier
  - Confidence: track kualitas data per frame
"""

import uuid
import numpy as np
from datetime import datetime
from typing import List, Optional, Tuple

from models.schemas import (
    Landmark, KinematicMetrics, ClinicalReport, RiskLevel
)
from core.angle_calculator import AngleCalculator
from core.tremor_analyzer import TremorAnalyzer
from core import asymmetry_index as asi_mod
from core.sit_to_stand import SitToStandDetector
from core.clinical_thresholds import STROKE, PARKINSON, CONFIDENCE
from core.risk_classifier import RiskClassifier

# ── MediaPipe landmark indices ───────────────────────────
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW,    R_ELBOW    = 13, 14
L_WRIST,    R_WRIST    = 15, 16
L_HIP,      R_HIP      = 23, 24
L_KNEE,     R_KNEE     = 25, 26
L_ANKLE,    R_ANKLE    = 27, 28


class KinematicEngine:
    """Engine komputasi kinematika per-sesi assessment."""

    def __init__(self, instruction: str, fps: int = 30, patient_age: int | None = None):
        self.instruction = instruction
        self.fps = fps
        self.patient_age = patient_age
        self.frame_count = 0
        self.created_at = datetime.now()

        # Sub-modules
        self.angle_calc = AngleCalculator()
        self.tremor_analyzer = TremorAnalyzer(fps=fps)
        self.sts_detector = SitToStandDetector(fps=fps)

        # Time-series buffers (max 5000 frame = ~167 detik)
        self._max_buffer = 5000
        self.angle_L_buf: List[float] = []
        self.angle_R_buf: List[float] = []
        self.asi_buf:     List[float] = []
        self.wrist_y_L:   List[float] = []
        self.wrist_y_R:   List[float] = []
        self.timestamps:  List[float] = []

        # Compute age-stratified STS threshold
        self._sts_warn = self._get_sts_threshold()
        
        # Initialize tracking variables
        self._init_tracking_vars()

    def _get_sts_threshold(self) -> float:
        """Get age-stratified STS warning threshold (detik)."""
        # Gunakan sistem clinical_thresholds baru
        from core.clinical_thresholds import SARCOPENIA
        th = SARCOPENIA.get_thresholds(self.patient_age)
        return th.monitor_max_s

    def _init_tracking_vars(self):
        """Init all tracking variables separately to fix indentation issues."""
        # Per-frame paired angles for accurate ASI
        self._paired_angles: List[Tuple[float, float]] = []

        # PSD cache — update setiap N frame
        self._psd_interval = max(30, self.fps * 2)  # Setiap 2 detik
        self._last_psd_frame = 0
        self._cached_psd_freqs: Optional[List[float]] = None
        self._cached_psd_power: Optional[List[float]] = None

        # Confidence tracking
        self._visibility_sum = 0.0
        self._visibility_count = 0

    def _to_dict(self, landmarks: List[Landmark]) -> dict:
        """Konversi list landmarks ke dict {id: np.array[xyz]} dengan confidence filter."""
        result = {}
        for lm in landmarks:
            if lm.vis >= CONFIDENCE.min_visibility:
                result[lm.id] = np.array([lm.x, lm.y, lm.z])
            # Track visibility for confidence scoring
            self._visibility_sum += lm.vis
            self._visibility_count += 1
        return result

    def _compute_angle(self, pts: dict, pivot_id: int, a_id: int, b_id: int) -> Optional[float]:
        """Hitung sudut di pivot_id dengan titik a_id dan b_id. Return None jika landmark tidak ada."""
        if all(i in pts for i in [pivot_id, a_id, b_id]):
            return self.angle_calc.compute(pts[a_id], pts[pivot_id], pts[b_id])
        return None

    def _update_psd(self) -> Tuple[Optional[List[float]], Optional[List[float]]]:
        """Compute Welch PSD jika ada cukup data. Return (freqs, power) atau (None, None)."""
        wrist = (self.wrist_y_L if len(self.wrist_y_L) >= len(self.wrist_y_R)
                 else self.wrist_y_R)

        if len(wrist) < self.fps * 2:
            return None, None

        freqs, psd = self.tremor_analyzer.welch_psd(np.array(wrist))
        if len(freqs) == 0:
            return None, None

        return freqs.tolist(), psd.tolist()

    def _compute_frame_confidence(self) -> float:
        """Compute current frame confidence level."""
        if self._visibility_count == 0:
            return 0.0
        avg_vis = self._visibility_sum / self._visibility_count
        frame_conf = min(1.0, self.frame_count / CONFIDENCE.high_confidence_frames)
        vis_conf = min(1.0, avg_vis / CONFIDENCE.excellent_visibility)
        return round((frame_conf * 0.4 + vis_conf * 0.6), 3)

    def process_frame(
        self, frame_id: int, timestamp: float, landmarks: List[Landmark]
    ) -> KinematicMetrics:
        """Proses satu frame landmark → hasilkan metrik kinematika."""
        self.frame_count += 1
        pts = self._to_dict(landmarks)
        self.timestamps.append(timestamp)

        m = KinematicMetrics(frame=frame_id)

        # ── A. Shoulder angles (Hip → Shoulder → Elbow) ──
        # Fallback: Jika pinggul tidak terlihat (sering terjadi jika duduk dekat kamera),
        # buat titik pinggul virtual tepat di bawah bahu.
        if L_HIP not in pts and L_SHOULDER in pts:
            pts[L_HIP] = pts[L_SHOULDER] + np.array([0, 0.5, 0])
        if R_HIP not in pts and R_SHOULDER in pts:
            pts[R_HIP] = pts[R_SHOULDER] + np.array([0, 0.5, 0])

        theta_L = self._compute_angle(pts, L_SHOULDER, L_HIP, L_ELBOW)
        theta_R = self._compute_angle(pts, R_SHOULDER, R_HIP, R_ELBOW)

        if theta_L is not None:
            m.shoulder_angle_L = theta_L
            self.angle_L_buf.append(theta_L)
            if len(self.angle_L_buf) > self._max_buffer:
                self.angle_L_buf.pop(0)

        if theta_R is not None:
            m.shoulder_angle_R = theta_R
            self.angle_R_buf.append(theta_R)
            if len(self.angle_R_buf) > self._max_buffer:
                self.angle_R_buf.pop(0)

        # ── B. Elbow angles (Shoulder → Elbow → Wrist) ──
        phi_L = self._compute_angle(pts, L_ELBOW, L_SHOULDER, L_WRIST)
        if phi_L is not None:
            m.elbow_angle_L = phi_L

        phi_R = self._compute_angle(pts, R_ELBOW, R_SHOULDER, R_WRIST)
        if phi_R is not None:
            m.elbow_angle_R = phi_R

        # ── C. Asymmetry Index (per-frame paired matching) ──
        if self.frame_count > 10:
            asi = None
            if theta_L is not None and theta_R is not None:
                # Both angles available in same frame → accurate pair
                asi = asi_mod.compute_from_angles(theta_L, theta_R)
                self._paired_angles.append((theta_L, theta_R))
                if len(self._paired_angles) > self._max_buffer:
                    self._paired_angles.pop(0)
            elif L_WRIST in pts and R_WRIST in pts:
                # Fallback: position-based ASI
                asi = asi_mod.compute_from_positions(pts[L_WRIST], pts[R_WRIST])

            if asi is not None:
                m.ASI = asi
                self.asi_buf.append(asi)
                if len(self.asi_buf) > self._max_buffer:
                    self.asi_buf.pop(0)

        # ── D. Wrist y-coordinates (untuk tremor analysis) ──
        if L_WRIST in pts:
            self.wrist_y_L.append(pts[L_WRIST][1])
        if R_WRIST in pts:
            self.wrist_y_R.append(pts[R_WRIST][1])

        # ── E. Tremor — live dominant frequency ──
        wrist = (self.wrist_y_L if len(self.wrist_y_L) >= len(self.wrist_y_R)
                 else self.wrist_y_R)
        if len(wrist) >= self.fps * 2:
            df, ta, tp = self.tremor_analyzer.analyze(np.array(wrist))
            if df is not None:
                m.dominant_freq_hz = df
                m.tremor_amplitude = ta

        # ── F. PSD update (setiap N frame) ──
        if self.frame_count - self._last_psd_frame >= self._psd_interval:
            psd_freqs, psd_power = self._update_psd()
            if psd_freqs is not None:
                self._cached_psd_freqs = psd_freqs
                self._cached_psd_power = psd_power
                m.psd_freqs = psd_freqs
                m.psd_power = psd_power
            self._last_psd_frame = self.frame_count

        # ── G. Sit-to-Stand detection ──
        if self.instruction == "sit_to_stand":
            if L_HIP in pts and R_HIP in pts:
                mid_y = (pts[L_HIP][1] + pts[R_HIP][1]) / 2.0
                phase, dur = self.sts_detector.update(mid_y)
                m.sts_phase = phase
                m.sts_duration = dur

        # ── H. Confidence ──
        m.confidence = self._compute_frame_confidence()

        # ── I. Status determination ──
        if m.ASI is not None and m.ASI > STROKE.asi_monitor_max:
            m.status = "alert_asymmetry"
        elif m.sts_duration is not None:
            from core.clinical_thresholds import SARCOPENIA
            group = SARCOPENIA.get_thresholds(self.patient_age)
            if m.sts_duration > group.monitor_max_s:
                m.status = "alert_slow"
        else:
            m.status = "recording"

        return m

    def finalize(self, patient_id: str = "") -> ClinicalReport:
        """Finalisasi sesi: hitung FFT, rata-rata metrik, klasifikasi risiko."""

        # ── 1. Tremor analysis (full session) ──
        wrist = (self.wrist_y_L if len(self.wrist_y_L) >= len(self.wrist_y_R)
                 else self.wrist_y_R)
        dom_freq = tremor_amp = tremor_pct = None
        if len(wrist) >= self.fps * 2:
            df, ta, tp = self.tremor_analyzer.analyze(np.array(wrist))
            dom_freq, tremor_amp, tremor_pct = df, ta, tp

        # ── 2. Averages (using paired angles when available) ──
        if self._paired_angles:
            paired_L = [p[0] for p in self._paired_angles]
            paired_R = [p[1] for p in self._paired_angles]
            mean_aL = float(np.mean(paired_L))
            mean_aR = float(np.mean(paired_R))
        else:
            mean_aL = float(np.mean(self.angle_L_buf)) if self.angle_L_buf else 0.0
            mean_aR = float(np.mean(self.angle_R_buf)) if self.angle_R_buf else 0.0

        mean_asi = float(np.mean(self.asi_buf)) if self.asi_buf else 0.0
        max_asi = float(np.max(self.asi_buf)) if self.asi_buf else 0.0
        angle_asym = abs(mean_aL - mean_aR)

        # ── 3. Sit-to-Stand summary ──
        sts_dur, sts_vel = self.sts_detector.get_summary()

        # ── 4. Risk classification (dataset-trained) ──
        stroke_risk, _, _ = RiskClassifier.classify_stroke(
            mean_asi, angle_asym, self.frame_count
        )
        parkinson_risk, _, _ = RiskClassifier.classify_parkinson(
            dom_freq, tremor_amp, tremor_pct or 0.0, self.frame_count
        )
        sarcopenia_risk, _, _ = RiskClassifier.classify_sarcopenia(
            sts_dur, self.patient_age
        )

        return ClinicalReport(
            session_id=str(uuid.uuid4()),
            patient_id=patient_id,
            timestamp=datetime.now(),
            instruction=self.instruction,
            meanASI=mean_asi,
            maxASI=max_asi,
            shoulder_angle_L_mean=mean_aL,
            shoulder_angle_R_mean=mean_aR,
            angle_asymmetry=angle_asym,
            dominant_freq=dom_freq,
            tremor_amplitude=tremor_amp,
            tremor_duration_pct=tremor_pct or 0.0,
            transition_duration=sts_dur,
            transition_velocity=sts_vel,
            stroke_risk=stroke_risk,
            parkinson_risk=parkinson_risk,
            sarcopenia_risk=sarcopenia_risk,
        )
