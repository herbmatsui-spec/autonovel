"""Impulse response synthesizer for narrative plot interventions."""

import numpy as np


def design_midpoint_disaster_impulse(
    length: int = 5,
    peak: float = 9.0,
    decay: float = 0.70,
    base: float = 0.0
) -> np.ndarray:
    """Design a synthetic disaster impulse response with sharp onset and exponential decay.

    Parameters:
        length: Number of episodes the disruption impacts.
        peak: Peak additive tension boost at impulse onset.
        decay: Decay factor per subsequent episode (0.0 < decay < 1.0).
        base: Baseline offset.

    Returns:
        1D NumPy array of length `length`.
    """
    if length <= 0:
        return np.array([], dtype=np.float64)

    impulse = np.zeros(length, dtype=np.float64)
    current = peak
    for i in range(length):
        impulse[i] = current
        current = max(0.0, current * decay)

    return impulse + base
