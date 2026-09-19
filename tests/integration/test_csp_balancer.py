"""Integration tests for CSP Narrative Balancer."""

import pytest
from src.narrative_balancer.csp.balancer import CSPNarrativeBalancer
from src.narrative_balancer.csp.config import CSPConfig
from src.narrative_balancer.csp.partial_state import PartialPlotState
from src.narrative_balancer.models import Beat, BeatType


def test_csp_balancer_complete_story():
    cfg = CSPConfig(n_episodes=20, midpoint_episode=10, midpoint_min_tension=7)
    balancer = CSPNarrativeBalancer(config=cfg)

    # Partial plot with only ep 1 and ep 20 confirmed
    partial = PartialPlotState(
        total_episodes=20,
        confirmed_beats={
            1: Beat(episode=1, tension=4.0, beat_type=BeatType.SETUP),
            20: Beat(episode=20, tension=9.0, beat_type=BeatType.CLIMAX),
        },
    )

    solved_beats = balancer.balance(partial)
    assert len(solved_beats) == 20
    assert solved_beats[0].episode == 1
    assert solved_beats[19].episode == 20
    # Check midpoint episode 10
    assert solved_beats[9].tension >= 7


def test_csp_balancer_repairs_midpoint_sag():
    cfg = CSPConfig(n_episodes=20, midpoint_episode=10, midpoint_min_tension=7)
    balancer = CSPNarrativeBalancer(config=cfg)

    # Feed a sag where midpoint was set to low daily
    sag_beats = [
        Beat(episode=i, tension=3.0, beat_type=BeatType.DAILY) for i in range(1, 21)
    ]
    repaired = balancer.balance(sag_beats)
    assert len(repaired) == 20
    # Repaired midpoint must satisfy tension >= 7
    assert repaired[9].tension >= 7
