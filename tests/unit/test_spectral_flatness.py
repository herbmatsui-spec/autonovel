"""Unit tests for signal extraction and spectral metrics."""

import numpy as np
import pytest
from src.narrative_balancer.dsp.models import Beat
from src.narrative_balancer.dsp.signal import extract_tension_curve
from src.narrative_balancer.dsp.spectral import (
    spectral_flatness,
    low_freq_energy_ratio,
    multivariate_spectral_flatness,
)


def test_extract_tension_curve():
    beats = [
        Beat(episode=1, tension=3.0),
        Beat(episode=2, tension=5.0),
        Beat(episode=3, tension=8.0),
    ]
    curve = extract_tension_curve(beats)
    assert np.allclose(curve, [3.0, 5.0, 8.0])


def test_spectral_flatness():
    # Pure tone (low flatness)
    t = np.linspace(0, 4 * np.pi, 64)
    sine_wave = np.sin(t) + 5.0
    sf_sine = spectral_flatness(sine_wave)

    # Uniform random noise (high flatness)
    np.random.seed(42)
    noise = np.random.uniform(2.0, 8.0, 64)
    sf_noise = spectral_flatness(noise)

    assert sf_sine < sf_noise
    assert 0.0 <= sf_sine <= 1.0
    assert 0.0 <= sf_noise <= 1.0


def test_low_freq_energy_ratio():
    t = np.linspace(0, 1, 64)
    # Slow trend (low frequency)
    slow_signal = np.sin(2 * np.pi * 1 * t) + 5.0
    ratio_slow = low_freq_energy_ratio(slow_signal, cutoff_ratio=0.3)

    # Fast oscillation (high frequency)
    fast_signal = np.sin(2 * np.pi * 20 * t) + 5.0
    ratio_fast = low_freq_energy_ratio(fast_signal, cutoff_ratio=0.3)

    assert ratio_slow > ratio_fast
    assert ratio_slow > 0.8
    assert ratio_fast < 0.3
