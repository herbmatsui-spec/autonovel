"""Unit tests for Arbitrator models."""

import pytest
from src.narrative_balancer.arbitrator.models import (
    PlotState,
    BalancerResult,
    ConflictRecord,
    IntegratedResult,
)
from src.narrative_balancer.models import Beat, BeatType, CorrectionAction


def test_plot_state_creation():
    beats = [
        Beat(episode=2, tension=5.0),
        Beat(episode=1, tension=4.0),
    ]
    state = PlotState.from_beats(beats, total_episodes=20)
    assert state.total_episodes == 20
    # Ordered by episode
    assert state.beats[0].episode == 1
    assert state.beats[1].episode == 2
    assert state.get_beat(1).tension == 4.0
    assert state.get_beat(99) is None


def test_balancer_result_and_conflict_models():
    res = BalancerResult(
        balancer_name="grammar",
        beats=[Beat(episode=1, tension=6.0)],
        detections_count=1,
        success=True,
    )
    assert res.balancer_name == "grammar"
    assert res.success is True

    record = ConflictRecord(
        episode=10,
        conflicting_balancers=["grammar", "dsp"],
        winning_balancer="grammar",
        chosen_action=CorrectionAction(
            episode=10,
            action_type="GRAMMAR_REWRITE",
            target_field="beat_type",
            original_value="DAILY",
            new_value="MIDPOINT_DISASTER",
        ),
        rationale="Grammar priority",
    )
    assert record.winning_balancer == "grammar"
