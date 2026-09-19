"""
Unit tests for TokenExpander, deterministic expansion, and nested tokens (PLAN_Y3 Step 4, 5, 6).
"""

import pytest
from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_tokens.expander import TokenExpander


def test_token_expansion_basic():
    expander = TokenExpander()
    raw = "「答えなさい」[BEAT:pause:short]「聞こえないの？」"
    expanded = expander.expand(raw, seed=10)
    assert "[BEAT:pause:short]" not in expanded
    assert "「答えなさい」" in expanded
    assert "「聞こえないの？」" in expanded


def test_deterministic_expansion_reproducibility():
    expander = TokenExpander()
    raw = "[SUBTEXT:irony]「それで？」"
    ctx = SubtextContext(scene_id="s_100", turn_index=3, speaker="Elena")

    res1 = expander.expand(raw, context=ctx)
    res2 = expander.expand(raw, context=ctx)
    assert res1 == res2, "Deterministic expansion must produce identical output for identical context"


def test_nested_token_expansion():
    expander = TokenExpander()
    # Mock nested token string
    raw = "[SUBTEXT:irony]"
    expanded = expander.expand(raw, seed=42, max_depth=3)
    assert "[" not in expanded or "]" not in expanded  # all tokens expanded
