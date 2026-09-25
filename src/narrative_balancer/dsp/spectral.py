"""Spectral analysis routines for narrative tension signals."""

from typing import Union
import numpy as np


def compute_psd(signal: np.ndarray) -> np.ndarray:
    """Compute one-sided Power Spectral Density (PSD) using FFT."""
    if len(signal) == 0:
        return np.array([], dtype=np.float64)

    # Detrend by removing DC mean to analyze AC variations, or keep DC if constant
    n = len(signal)
    fft_vals = np.fft.rfft(signal)
    psd = (np.abs(fft_vals) ** 2) / float(n)
    return psd


def spectral_flatness(curve: np.ndarray, eps: float = 1e-10) -> float:
    """Compute Spectral Flatness Measure (Wiener entropy) of a 1D curve.

    Defined as: geometric_mean(psd) / arithmetic_mean(psd).
    Output bounded in [0.0, 1.0].
    - Pure tones / pure single frequency: ~ 0.0
    - White noise / completely flat spectrum: ~ 1.0
    - Constant / flat signals: 0.0 (no spectral variation)
    """
    if len(curve) < 2:
        return 0.0

    # If the curve is completely flat, it has zero high-frequency dynamics
    # When analyzing tension sag, a constant plateau can be detected or treated as flat DC
    # In DSP flatness:
    psd = compute_psd(curve)
    if len(psd) == 0 or np.all(psd < eps):
        return 0.0

    # Avoid zero division and log(0)
    psd_safe = np.maximum(psd, eps)
    arithmetic_mean = np.mean(psd_safe)
    if arithmetic_mean < eps:
        return 0.0

    log_mean = np.mean(np.log(psd_safe))
    geometric_mean = np.exp(log_mean)

    flatness = float(geometric_mean / arithmetic_mean)
    return float(np.clip(flatness, 0.0, 1.0))


def low_freq_energy_ratio(curve: np.ndarray, cutoff_ratio: float = 0.3, eps: float = 1e-10) -> float:
    """Compute the ratio of energy concentrated in low frequencies (below cutoff_ratio).

    Low frequencies correspond to slow macro-trends or sagging plateaus without rapid turns.
    cutoff_ratio: Fraction of the Nyquist spectrum considered 'low frequency' (default: 0.3).
    """
    if len(curve) < 2:
        return 1.0

    # Detrend DC offset to measure dynamic AC power distribution
    ac_signal = curve - np.mean(curve)
    psd = compute_psd(ac_signal)
    total_energy = np.sum(psd)
    if total_energy < eps:
        return 1.0

    cutoff_bin = max(1, int(np.ceil(len(psd) * cutoff_ratio)))
    low_energy = np.sum(psd[:cutoff_bin])

    ratio = float(low_energy / total_energy)
    return float(np.clip(ratio, 0.0, 1.0))


def multivariate_spectral_flatness(curves: np.ndarray, eps: float = 1e-10) -> float:
    """Multivariate spectral flatness across multiple channels (e.g. tension, stakes, pacing).

    curves: 2D array of shape (n_channels, n_episodes).
    """
    if curves.ndim == 1:
        return spectral_flatness(curves, eps=eps)

    n_channels = curves.shape[0]
    if n_channels == 0:
        return 0.0

    flatness_scores = [spectral_flatness(curves[i], eps=eps) for i in range(n_channels)]
    # Geometric mean of channel spectral flatness
    log_scores = [np.log(max(s, eps)) for s in flatness_scores]
    return float(np.clip(np.exp(np.mean(log_scores)), 0.0, 1.0))
