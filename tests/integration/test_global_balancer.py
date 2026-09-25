"""Integration tests for GlobalNarrativeBalancer."""

import pytest
from src.narrative_balancer.arbitrator.balancer import GlobalNarrativeBalancer
from src.narrative_balancer.arbitrator.models import PlotState
from src.narrative_balancer.models import Beat, BeatType


def test_global_narrative_balancer_orchestrate():
    balancer = GlobalNarrativeBalancer()

    # 40 episodes with mid-arc stagnation (ep 15 to 25)
    beats = [
        Beat(episode=i, tension=3.0, beat_type=BeatType.DAILY) for i in range(1, 41)
    ]
    beats[39] = Beat(episode=40, tension=9.0, beat_type=BeatType.CLIMAX)

    plot_state = PlotState.from_beats(beats, total_episodes=40)
    integrated = balancer.orchestrate(plot_state)

    assert len(integrated.balanced_beats) == 40
    # Ensure midpoint crisis exists
    mid_beats = [b for b in integrated.balanced_beats if 18 <= b.episode <= 22]
    max_mid_tension = max((b.tension for b in mid_beats), default=0.0)
    assert max_mid_tension >= 7.0

    # Ensure applied actions were logged
    assert len(integrated.applied_actions) > 0
    # All 3 balancers should have run
    assert "grammar" in integrated.balancer_results
    assert "dsp" in integrated.balancer_results
    assert "csp" in integrated.balancer_results
