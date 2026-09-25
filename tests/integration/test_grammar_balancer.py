"""Unit tests for incremental parsing and integration test for grammar balancer."""

import pytest
from src.narrative_balancer.grammar.balancer import GrammarNarrativeBalancer
from src.narrative_balancer.grammar.incremental import IncrementalParser
from src.narrative_balancer.grammar.symbols import Terminal
from src.narrative_balancer.models import Beat, BeatType


def test_incremental_parser():
    inc = IncrementalParser()
    f1 = inc.add_terminal(Terminal.SETUP)
    assert f1.consumed_terminals == 1

    f2 = inc.add_terminal(Terminal.RISING)
    assert f2.consumed_terminals == 2

    f3 = inc.add_terminal(Terminal.BATTLE)
    assert f3.consumed_terminals == 3
    assert f3.is_valid_prefix is True


def test_grammar_balancer_end_to_end():
    balancer = GrammarNarrativeBalancer()
    # Stagnant 20-episode story with sagging mid-arc
    beats = [
        Beat(episode=i, tension=3.0, beat_type=BeatType.DAILY) for i in range(1, 21)
    ]
    # Set final climax
    beats[19] = Beat(episode=20, tension=9.0, beat_type=BeatType.CLIMAX)

    analysis_before = balancer.analyze_only(beats)
    assert analysis_before.total_cost > 0.0

    balanced = balancer.balance(beats, target_total_episodes=20)
    assert len(balanced) == 20

    # Ensure Midpoint disaster is present in middle
    mid_beats = balanced[5:15]
    has_disaster = any(b.beat_type in (BeatType.MIDPOINT_DISASTER, BeatType.DISASTER) for b in mid_beats)
    assert has_disaster is True
