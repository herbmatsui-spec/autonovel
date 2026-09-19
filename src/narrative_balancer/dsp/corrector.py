"""Convolution and writeback corrector for DSP tension balancer."""

from typing import List, Set
import numpy as np
from src.narrative_balancer.dsp.models import Beat, BeatType, CorrectionAction


def apply_impulse_correction(
    curve: np.ndarray,
    ep: int,
    impulse: np.ndarray,
    min_clip: float = 1.0,
    max_clip: float = 10.0,
) -> np.ndarray:
    """Apply an impulse response onto a tension curve starting at episode `ep` (0-based).

    Limits values within [min_clip, max_clip].
    """
    if len(curve) == 0 or len(impulse) == 0:
        return curve.copy()

    corrected = curve.copy()
    n = len(curve)
    m = len(impulse)

    if ep < 0 or ep >= n:
        return corrected

    end_idx = min(n, ep + m)
    impulse_slice_len = end_idx - ep
    # Add impulse
    corrected[ep:end_idx] += impulse[:impulse_slice_len]

    # Clip to valid narrative tension bounds
    np.clip(corrected, min_clip, max_clip, out=corrected)
    return corrected


def writeback_corrected_beats(
    original: List[Beat],
    corrected_curve: np.ndarray,
    corrected_eps: Set[int],
) -> List[Beat]:
    """Write back corrected tension values and updated beat types into Beat objects.

    Non-corrected episodes are copied without alteration.
    corrected_eps is a set of 1-based episode indices that received corrections.
    """
    new_beats: List[Beat] = []

    for i, orig_beat in enumerate(original):
        ep = orig_beat.episode  # 1-based
        if ep in corrected_eps and i < len(corrected_curve):
            new_tension = round(float(corrected_curve[i]), 2)
            # Create updated beat copy
            updated = orig_beat.model_copy(deep=True)
            updated.tension = new_tension

            # If this is the epicenter of a major impulse (high tension boost in mid-story), mark as MIDPOINT_DISASTER
            if new_tension >= 8.0 and orig_beat.beat_type in [BeatType.DAILY, BeatType.SETUP, BeatType.STAGNATION]:
                updated.beat_type = BeatType.MIDPOINT_DISASTER
                if not updated.summary:
                    updated.summary = "中盤崩壊・大打撃イベント（DSPインパルス補正）"

            new_beats.append(updated)
        else:
            new_beats.append(orig_beat.model_copy(deep=True))

    return new_beats
