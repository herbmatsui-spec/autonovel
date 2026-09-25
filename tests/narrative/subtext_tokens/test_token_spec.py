"""
Unit tests for Token BNF parser and specification (PLAN_Y3 Step 1).
"""

import pytest
from src.narrative.subtext_tokens.parser import TokenParser, TokenSpec


def test_token_bnf_parser_valid_cases():
    valid_tokens = [
        ("[SUBTEXT:irony]", "SUBTEXT", "irony", []),
        ("[BEAT:pause:short]", "BEAT", "pause", ["short"]),
        ("[ACTION:hide_hands:trembling]", "ACTION", "hide_hands", ["trembling"]),
        ("[GLANCE:away:down]", "GLANCE", "away", ["down"]),
        ("[PAUSE:breath]", "PAUSE", "breath", []),
        ("[IRONY:cold_acceptance]", "IRONY", "cold_acceptance", []),
        ("[INTERNAL:suppressed_rage]", "INTERNAL", "suppressed_rage", []),
    ]
    for raw, cat, key, mods in valid_tokens:
        assert TokenParser.is_valid_token(raw) is True
        spec = TokenParser.parse(raw)
        assert spec is not None
        assert spec.category == cat
        assert spec.key == key
        assert spec.modifiers == mods


def test_token_bnf_parser_invalid_cases():
    invalid_tokens = [
        "[UNKNOWN:irony]",  # Unknown category
        "[:irony]",         # Missing category
        "[BEAT:]",          # Missing key
        "[BEAT:UPPERCASE]", # Key not lowercase
        "BEAT:pause",       # Missing brackets
    ]
    for raw in invalid_tokens:
        assert TokenParser.is_valid_token(raw) is False
        assert TokenParser.parse(raw) is None


def test_find_tokens_in_text():
    sample = "「何の話だ」[BEAT:pause:short]「君の言う通りにする」[GLANCE:away]"
    tokens = TokenParser.find_tokens(sample)
    assert len(tokens) == 2
    assert tokens[0].category == "BEAT"
    assert tokens[1].category == "GLANCE"
