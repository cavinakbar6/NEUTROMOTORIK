"""
AsymmetryIndex — Indeks asimetri bilateral untuk deteksi stroke ringan.

Rumus:
    ASI = 2 * |v_L - v_R| / (v_L + v_R + epsilon)

Threshold (literatur klinis):
    ASI < 0.10  → Normal (simetris)
    ASI 0.10–0.15 → Perlu evaluasi lanjutan
    ASI > 0.15  → Asimetri signifikan (indikasi stroke ringan / TIA)
"""

import numpy as np

_EPSILON = 1e-6


def compute_from_angles(angle_L: float, angle_R: float) -> float:
    """ASI dari perbandingan sudut kiri vs kanan."""
    num = 2.0 * abs(angle_L - angle_R)
    den = angle_L + angle_R + _EPSILON
    return float(num / den)


def compute_from_positions(wrist_L: np.ndarray, wrist_R: np.ndarray) -> float:
    """ASI dari magnitudo posisi 3D pergelangan tangan."""
    mag_L = float(np.linalg.norm(wrist_L))
    mag_R = float(np.linalg.norm(wrist_R))
    num = 2.0 * abs(mag_L - mag_R)
    den = mag_L + mag_R + _EPSILON
    return float(num / den)


def compute_timeseries(angles_L: list, angles_R: list) -> np.ndarray:
    """Hitung time series ASI dari buffer sudut."""
    n = min(len(angles_L), len(angles_R))
    if n == 0:
        return np.array([])
    return np.array([
        compute_from_angles(angles_L[i], angles_R[i]) for i in range(n)
    ])
