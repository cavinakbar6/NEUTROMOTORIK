"""
TremorAnalyzer — Deteksi frekuensi tremor menggunakan Fast Fourier Transform (FFT).

Karakteristik tremor Parkinson: 4–12 Hz.
Pipeline:
    1. Remove DC component
    2. Apply Hanning window (reduce spectral leakage)
    3. Compute FFT
    4. Find dominant frequency in tremor zone (3-15 Hz)
    5. Compute amplitude and relative duration
"""

import numpy as np
from scipy import signal as sig
from scipy.fft import fft, fftfreq
from typing import Tuple, Optional


class TremorAnalyzer:

    FREQ_MIN = 3.0    # Hz — lower bound pencarian
    FREQ_MAX = 15.0   # Hz — upper bound pencarian
    PARK_MIN = 4.0    # Hz — zona khas Parkinson
    PARK_MAX = 12.0   # Hz

    def __init__(self, fps: int = 30):
        self.fps = fps
        self.nyquist = fps / 2.0

    def analyze(
        self, y_series: np.ndarray
    ) -> Tuple[Optional[float], Optional[float], float]:
        """
        Analisis FFT time-series koordinat y pergelangan tangan.
        Returns: (dominant_freq_hz, tremor_amplitude, tremor_duration_pct)
        None jika data tidak cukup.
        """
        N = len(y_series)
        if N < self.fps * 2:  # Minimal 2 detik
            return None, None, 0.0

        # 1. Remove DC component
        y_centered = y_series - np.mean(y_series)

        # 2. Hanning window
        window = np.hanning(N)
        y_windowed = y_centered * window

        # 3. FFT
        Y = fft(y_windowed)
        freqs = fftfreq(N, d=1.0 / self.fps)

        # 4. Positive frequencies only
        pos_mask = freqs > 0
        freqs_pos = freqs[pos_mask]
        power = np.abs(Y[pos_mask]) ** 2 / N

        # 5. Filter dalam zona tremor
        tremor_mask = (freqs_pos >= self.FREQ_MIN) & (freqs_pos <= self.FREQ_MAX)
        f_tremor = freqs_pos[tremor_mask]
        p_tremor = power[tremor_mask]

        if len(f_tremor) == 0:
            return None, None, 0.0

        # 6. Frekuensi dominan dalam zona tremor
        idx = np.argmax(p_tremor)
        dominant_freq = float(f_tremor[idx])

        # 7. Amplitudo (dari power spectrum)
        amplitude = float(np.sqrt(2.0 * p_tremor[idx]))

        # 8. Durasi relatif (% energi tremor / energi total)
        total_energy = float(np.sum(power))
        tremor_energy = float(np.sum(p_tremor))
        pct = tremor_energy / total_energy if total_energy > 1e-10 else 0.0

        return dominant_freq, amplitude, pct

    def welch_psd(
        self, y_series: np.ndarray, nperseg: int = 256
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Power Spectral Density via Welch's method. Lebih robust terhadap noise."""
        n = min(nperseg, len(y_series))
        if n < 8:
            return np.array([]), np.array([])
        freqs, psd = sig.welch(
            y_series - np.mean(y_series),
            fs=self.fps,
            nperseg=n,
            window="hann",
        )
        return freqs, psd
