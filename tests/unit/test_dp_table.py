"""Unit tests for DP table, cost model and rewrite rules."""

import pytest
from src.narrative_balancer.grammar.cost_model import GrammarCostModel
from src.narrative_balancer.grammar.dp import build_dp_table
from src.narrative_balancer.grammar.rewrite_rules import REWRITE_RULES
from src.narrative_balancer.grammar.rewriter import GrammarRewriter
from src.narrative_balancer.grammar.symbols import NonTerminal, Terminal
from src.narrative_balancer.models import Beat, BeatType


def test_dp_table_construction():
    cost_model = GrammarCostModel()
    dp = build_dp_table(max_len=10, cost_model=cost_model)

    # Cost of terminal of length 1 is 0.0
    assert dp.get_cost(Terminal.SETUP, 1) == 0.0
    # ACT1 of length 3 should have a finite cost
    cost_act1 = dp.get_cost(NonTerminal.ACT1, 3)
    assert cost_act1 < float("inf")


def test_rewrite_rules_application():
    rewriter = GrammarRewriter()
    # Stagnant middle episode at index 10 (ep 11 of 20)
    beats = [Beat(episode=i, beat_type=BeatType.SETUP) for i in range(1, 21)]
    beats[9] = Beat(episode=10, beat_type=BeatType.STAGNATION)

    rewritten, actions = rewriter.apply_best_rewrites(beats)
    assert len(rewritten) == 20
    assert len(actions) >= 1
    # Ep 10 was rewritten to MIDPOINT_DISASTER
    assert rewritten[9].beat_type == BeatType.MIDPOINT_DISASTER
