"""Unit tests for DSP models."""

import pytest
import numpy as np
from src.narrative_balancer.dsp.models import (
    Beat,
    BeatType,
    CorrectionAction,
    DSPConfig,
    ImpulseConfig,
    SagDetection,
    TensionSignal,
)


def test_tension_signal_serialization():
    signal = TensionSignal(episodes=[1, 2, 3], values=[4.0, 5.5, 7.0])
    arr = signal.to_numpy()
    assert isinstance(arr, np.ndarray)
    assert np.allclose(arr, [4.0, 5.5, 7.0])

    data = signal.model_dump()
    restored = TensionSignal.model_validate(data)
    assert restored.episodes == [1, 2, 3]
    assert restored.values == [4.0, 5.5, 7.0]


def test_beat_model_validation():
    beat = Beat(episode=1, tension=6.5, beat_type=BeatType.SETUP, characters=["Hero"])
    assert beat.episode == 1
    assert beat.tension == 6.5
    assert beat.beat_type == BeatType.SETUP

    data = beat.model_dump()
    assert data["episode"] == 1
    assert data["characters"] == ["Hero"]


def test_sag_detection_model():
    sag = SagDetection(
        start_episode=15,
        end_episode=22,
        detected_episode=18,
        spectral_flatness=0.72,
        low_freq_ratio=0.81,
        is_sag=True,
        reason="Test sag",
    )
    assert sag.is_sag is True
    assert sag.start_episode == 15
