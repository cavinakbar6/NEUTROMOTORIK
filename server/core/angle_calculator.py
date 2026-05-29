"""
AngleCalculator — Menghitung sudut sendi menggunakan dot product vektor.

Rumus:
    θ = arccos( (BA · BC) / (|BA| × |BC|) )

Dimana B = pivot (titik sendi).

Landmark Mapping (MediaPipe):
    Shoulder angle: Hip → Shoulder → Elbow  (pivot = Shoulder)
    Elbow angle:    Shoulder → Elbow → Wrist (pivot = Elbow)
    Hip angle:      Shoulder → Hip → Knee   (pivot = Hip)
    Knee angle:     Hip → Knee → Ankle      (pivot = Knee)
"""

import numpy as np
from typing import Optional


class AngleCalculator:

    @staticmethod
    def compute(A: np.ndarray, B: np.ndarray, C: np.ndarray) -> float:
        """
        Hitung sudut di titik B (pivot) dalam derajat.
        A, B, C: numpy array [x, y, z].
        Returns: sudut 0.0 — 180.0 derajat.
        """
        BA = A - B
        BC = C - B

        norm_BA = np.linalg.norm(BA)
        norm_BC = np.linalg.norm(BC)

        if norm_BA < 1e-8 or norm_BC < 1e-8:
            return 0.0

        cosine = np.dot(BA, BC) / (norm_BA * norm_BC)
        cosine = float(np.clip(cosine, -1.0, 1.0))
        return float(np.degrees(np.arccos(cosine)))

    def compute_all(self, pts: dict) -> dict:
        """
        Hitung semua sudut kunci dari dict landmark.
        pts: {landmark_id: np.array([x, y, z])}
        """
        angles = {}

        # Shoulder flexion (Hip → Shoulder → Elbow, pivot = Shoulder)
        if all(i in pts for i in [23, 11, 13]):
            angles["shoulder_L"] = self.compute(pts[23], pts[11], pts[13])
        if all(i in pts for i in [24, 12, 14]):
            angles["shoulder_R"] = self.compute(pts[24], pts[12], pts[14])

        # Elbow angle (Shoulder → Elbow → Wrist, pivot = Elbow)
        if all(i in pts for i in [11, 13, 15]):
            angles["elbow_L"] = self.compute(pts[11], pts[13], pts[15])
        if all(i in pts for i in [12, 14, 16]):
            angles["elbow_R"] = self.compute(pts[12], pts[14], pts[16])

        # Hip angle (Shoulder → Hip → Knee, pivot = Hip)
        if all(i in pts for i in [11, 23, 25]):
            angles["hip_L"] = self.compute(pts[11], pts[23], pts[25])
        if all(i in pts for i in [12, 24, 26]):
            angles["hip_R"] = self.compute(pts[12], pts[24], pts[26])

        # Knee angle (Hip → Knee → Ankle, pivot = Knee)
        if all(i in pts for i in [23, 25, 27]):
            angles["knee_L"] = self.compute(pts[23], pts[25], pts[27])
        if all(i in pts for i in [24, 26, 28]):
            angles["knee_R"] = self.compute(pts[24], pts[26], pts[28])

        return angles
