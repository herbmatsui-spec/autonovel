"""Scenario tests for Global Narrative Balancer arbitration."""

import pytest

pytest.importorskip("ortools")

from src.narrative_balancer.arbitrator.balancer import GlobalNarrativeBalancer
from src.narrative_balancer.arbitrator.models import PlotState
from src.narrative_balancer.models import Beat, BeatType


def test_scenario_normal_progression():
    """Scenario 1: Already well-structured plot needs minimal adjustments."""
    balancer = GlobalNarrativeBalancer()
    beats = [
        Beat(episode=i, tension=4.0 + (i % 4), beat_type=BeatType.SETUP if i < 15 else (BeatType.BATTLE if i < 30 else BeatType.CLIMAX))
        for i in range(1, 41)
    ]
    beats[19] = Beat(episode=20, tension=8.5, beat_type=BeatType.MIDPOINT_DISASTER)
    beats[39] = Beat(episode=40, tension=9.5, beat_type=BeatType.CLIMAX)

    res = balancer.orchestrate(beats)
    assert len(res.balanced_beats) == 40
    # Core milestones retained
    assert res.balanced_beats[19].beat_type == BeatType.MIDPOINT_DISASTER
    assert res.balanced_beats[39].beat_type == BeatType.CLIMAX


def test_scenario_midpoint_sag_resolution():
    """Scenario 2: Mid-story sag resolved with grammar priority disaster and DSP impulse."""
    balancer = GlobalNarrativeBalancer()
    # Stagnant episodes from 15 to 25
    beats = [
        Beat(episode=i, tension=3.0, beat_type=BeatType.DAILY) for i in range(1, 41)
    ]
    beats[39] = Beat(episode=40, tension=9.0, beat_type=BeatType.CLIMAX)

    res = balancer.orchestrate(beats)
    # Episode 20 must be resolved into high-tension disaster
    ep20 = res.balanced_beats[19]
    assert ep20.tension >= 7.0
    assert len(res.applied_actions) > 0
