"""Unit tests for PriorityResolver."""

import pytest
from src.narrative_balancer.arbitrator.config import ArbitratorConfig
from src.narrative_balancer.arbitrator.models import BalancerResult, PlotState
from src.narrative_balancer.arbitrator.resolver import PriorityResolver
from src.narrative_balancer.models import Beat, BeatType


def test_priority_resolver_conflict():
    config = ArbitratorConfig(priority_order=["grammar", "csp", "dsp"])
    resolver = PriorityResolver(config)

    orig_beats = [
        Beat(episode=i, tension=4.0, beat_type=BeatType.SETUP) for i in range(1, 11)
    ]
    orig_state = PlotState.from_beats(orig_beats, total_episodes=10)

    # At ep 5:
    # Grammar wants MIDPOINT_DISASTER
    # DSP wants tension boost to 9.0
    # CSP wants BATTLE
    grammar_beats = [b.model_copy(deep=True) for b in orig_beats]
    grammar_beats[4].beat_type = BeatType.MIDPOINT_DISASTER

    dsp_beats = [b.model_copy(deep=True) for b in orig_beats]
    dsp_beats[4].tension = 9.0

    csp_beats = [b.model_copy(deep=True) for b in orig_beats]
    csp_beats[4].beat_type = BeatType.BATTLE

    results = {
        "grammar": BalancerResult(balancer_name="grammar", beats=grammar_beats, success=True),
        "dsp": BalancerResult(balancer_name="dsp", beats=dsp_beats, success=True),
        "csp": BalancerResult(balancer_name="csp", beats=csp_beats, success=True),
    }

    resolved_beats, actions, conflicts = resolver.resolve(orig_state, results)

    assert len(resolved_beats) == 10
    # Ep 5 conflict: Grammar should win the beat_type
    ep5 = resolved_beats[4]
    assert ep5.beat_type == BeatType.MIDPOINT_DISASTER
    # And synthesize DSP's tension boost
    assert ep5.tension >= 9.0
    assert len(conflicts) >= 1
    assert conflicts[0].winning_balancer == "grammar"
