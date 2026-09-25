"""Unit tests for detector, impulse, corrector, writeback, and edge cases."""

import numpy as np
import pytest
from src.narrative_balancer.dsp.models import Beat, BeatType, DSPConfig
from src.narrative_balancer.dsp.detector import detect_sag, scan_sags
from src.narrative_balancer.dsp.impulse import design_midpoint_disaster_impulse
from src.narrative_balancer.dsp.corrector import apply_impulse_correction, writeback_corrected_beats
from src.narrative_balancer.dsp.signal import extract_tension_curve
from src.narrative_balancer.dsp.spectral import multivariate_spectral_flatness


def test_sag_detector():
    cfg = DSPConfig(window_size=8)
    # Normal dynamic curve: 4 -> 8 -> 5 -> 9 -> 4 -> 8 -> 6 -> 9
    dynamic_curve = np.array([4.0, 8.0, 5.0, 9.0, 4.0, 8.0, 6.0, 9.0, 7.0, 9.0])
    sags_dyn = scan_sags(dynamic_curve, cfg)
    assert len(sags_dyn) == 0

    # Flat stagnant middle section (sag): 40 episodes with sag from ep 15 to 25
    sag_curve = np.array([5.0] * 10 + [3.0] * 15 + [7.0] * 15)
    sags = scan_sags(sag_curve, cfg)
    assert len(sags) > 0


def test_impulse_design():
    impulse = design_midpoint_disaster_impulse(length=5, peak=9.0, decay=0.7)
    assert len(impulse) == 5
    assert impulse[0] == 9.0
    assert impulse[1] == pytest.approx(9.0 * 0.7)
    assert impulse[2] < impulse[1]


def test_corrector_clipping():
    curve = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
    impulse = np.array([8.0, 6.0, 4.0])
    corrected = apply_impulse_correction(curve, 1, impulse, min_clip=1.0, max_clip=10.0)

    # 5.0 + 8.0 = 13.0 -> clipped to 10.0
    assert corrected[1] == 10.0
    assert corrected[0] == 5.0  # untouched
    assert corrected[4] == 5.0  # untouched


def test_writeback():
    beats = [
        Beat(episode=1, tension=4.0, beat_type=BeatType.SETUP),
        Beat(episode=2, tension=4.0, beat_type=BeatType.DAILY),
        Beat(episode=3, tension=4.0, beat_type=BeatType.DAILY),
    ]
    corrected_curve = np.array([4.0, 9.0, 6.3])
    updated = writeback_corrected_beats(beats, corrected_curve, corrected_eps={2})

    assert updated[0].tension == 4.0
    assert updated[1].tension == 9.0
    assert updated[1].beat_type == BeatType.MIDPOINT_DISASTER
    assert updated[2].tension == 4.0  # untouched


def test_nan_handling():
    beats = [
        Beat(episode=1, tension=4.0),
        Beat(episode=2, tension=float("nan")),
        Beat(episode=3, tension=8.0),
    ]
    curve = extract_tension_curve(beats)
    assert not np.any(np.isnan(curve))
    # Linearly interpolated value between 4.0 and 8.0
    assert curve[1] == pytest.approx(6.0)


def test_multivariate_spectral():
    ch1 = np.sin(np.linspace(0, 4 * np.pi, 32)) + 5.0
    ch2 = np.random.uniform(2.0, 8.0, 32)
    multivar = np.vstack([ch1, ch2])
    score = multivariate_spectral_flatness(multivar)
    assert 0.0 <= score <= 1.0


@pytest.mark.parametrize("length", [1, 5, 10, 39, 40])
def test_edge_cases_lengths(length):
    beats = [Beat(episode=i + 1, tension=5.0) for i in range(length)]
    cfg = DSPConfig(window_size=8)
    curve = extract_tension_curve(beats)
    sags = scan_sags(curve, cfg)
    # Should not crash on boundary lengths
    assert isinstance(sags, list)
