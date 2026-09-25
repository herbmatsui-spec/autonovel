"""Unit tests for grammar symbols, rules and parser."""

import pytest
from src.narrative_balancer.grammar.symbols import NonTerminal, Terminal
from src.narrative_balancer.grammar.rules import GRAMMAR
from src.narrative_balancer.grammar.parser import EarleyParser


def test_symbols_and_rules():
    assert NonTerminal.STORY in GRAMMAR
    assert len(GRAMMAR[NonTerminal.STORY]) >= 1
    assert Terminal.MIDPOINT_DISASTER == "MIDPOINT_DISASTER"


def test_earley_parser_prefix():
    parser = EarleyParser()
    # Typical valid prefix: SETUP -> RISING -> BATTLE
    tokens = [Terminal.SETUP, Terminal.RISING, Terminal.BATTLE]
    forest = parser.parse_prefix(tokens)

    assert forest.consumed_terminals == 3
    assert forest.is_valid_prefix is True
    # NonTerminal.ACT1 should be completed by these 3 tokens
    assert NonTerminal.ACT1 in forest.completed_nonterminals


def test_earley_parser_empty():
    parser = EarleyParser()
    forest = parser.parse_prefix([])
    assert forest.consumed_terminals == 0
    assert forest.is_valid_prefix is True
