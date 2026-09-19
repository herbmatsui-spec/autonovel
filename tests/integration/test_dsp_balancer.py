"""Integration tests for DSP Tension Balancer end-to-end flow."""

import pytest
from src.narrative_balancer.dsp.balancer import DSPTensionBalancer
from src.narrative_balancer.dsp.models import Beat, BeatType, DSPConfig


def test_end_to_end_dsp_balance():
    # 40 episodes story with deliberate mid-story sag between ep 15 and 25
    beats = []
    for ep in range(1, 41):
        if 15 <= ep <= 25:
            # Stagnant middle section
            beats.append(Beat(episode=ep, tension=3.0, beat_type=BeatType.DAILY, title=f"Ep {ep} Stagnation"))
        elif ep >= 35:
            beats.append(Beat(episode=ep, tension=8.5, beat_type=BeatType.CLIMAX, title=f"Ep {ep} Climax"))
        else:
            beats.append(Beat(episode=ep, tension=5.0, beat_type=BeatType.SETUP, title=f"Ep {ep}"))

    balancer = DSPTensionBalancer(DSPConfig(window_size=8))
    sags = balancer.analyze(beats)
    assert len(sags) > 0

    corrected = balancer.correct(beats)
    assert len(corrected) == 40

    # Ensure sag in middle section was boosted
    mid_tensions = [b.tension for b in corrected if 15 <= b.episode <= 25]
    assert max(mid_tensions) > 8.0

    # Non-sag sections remain within normal range
    assert corrected[0].tension == 5.0
    assert corrected[39].tension == 8.5
