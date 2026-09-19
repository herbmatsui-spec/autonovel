"""Unit tests for balancer adapters."""

import pytest
from src.narrative_balancer.arbitrator.models import PlotState
from src.narrative_balancer.arbitrator.ports import (
    CSPAdapter,
    DSPAdapter,
    GrammarAdapter,
    NarrativeBalancerPort,
)
from src.narrative_balancer.models import Beat, BeatType


def test_adapters_satisfy_port():
    dsp = DSPAdapter()
    csp = CSPAdapter()
    grammar = GrammarAdapter()

    assert isinstance(dsp, NarrativeBalancerPort)
    assert isinstance(csp, NarrativeBalancerPort)
    assert isinstance(grammar, NarrativeBalancerPort)


def test_adapters_execution():
    beats = [
        Beat(episode=i, tension=3.0, beat_type=BeatType.DAILY) for i in range(1, 21)
    ]
    state = PlotState.from_beats(beats, total_episodes=20)

    dsp = DSPAdapter()
    res_dsp = dsp.balance(state)
    assert res_dsp.success is True
    assert len(res_dsp.beats) == 20

    grammar = GrammarAdapter()
    res_grammar = grammar.balance(state)
    assert res_grammar.success is True
    assert len(res_grammar.beats) == 20
