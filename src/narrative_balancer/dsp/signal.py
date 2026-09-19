"""Signal extraction and preprocessing utilities."""

from typing import List, Optional
import numpy as np
from src.narrative_balancer.dsp.models import Beat


def extract_tension_curve(beats: List[Beat], default_tension: float = 5.0) -> np.ndarray:
    """Extract tension values from a sequence of Beats into a 1D NumPy array.

    Handles empty sequences, NaN, and missing values by linear interpolation
    or fallback to default_tension.
    """
    if not beats:
        return np.array([], dtype=np.float64)

    values = []
    for b in beats:
        val = getattr(b, "tension", None)
        if val is None or np.isnan(val):
            values.append(np.nan)
        else:
            values.append(float(val))

    arr = np.array(values, dtype=np.float64)

    # Handle NaNs and missing values
    nans = np.isnan(arr)
    if np.all(nans):
        arr[:] = default_tension
    elif np.any(nans):
        # Linear interpolation for NaNs
        indices = np.arange(len(arr))
        valid_idx = indices[~nans]
        valid_vals = arr[~nans]
        arr[nans] = np.interp(indices[nans], valid_idx, valid_vals)

    return arr
