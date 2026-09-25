"""Property-based tests for DSP balancer components using Hypothesis."""

import numpy as np
from hypothesis import given, strategies as st
from src.narrative_balancer.dsp.spectral import spectral_flatness, low_freq_energy_ratio


@given(st.lists(st.floats(min_value=0.0, max_value=10.0, allow_nan=False), min_size=4, max_size=50))
def test_spectral_flatness_bounds(values):
    arr = np.array(values, dtype=np.float64)
    sf = spectral_flatness(arr)
    assert 0.0 <= sf <= 1.0


@given(st.lists(st.floats(min_value=0.0, max_value=10.0, allow_nan=False), min_size=4, max_size=50))
def test_low_freq_ratio_bounds(values):
    arr = np.array(values, dtype=np.float64)
    lfr = low_freq_energy_ratio(arr)
    assert 0.0 <= lfr <= 1.0
