"""
Unit tests for ContextMatcher (PLAN_Y2 Step 4, 15, 17).
"""

from pathlib import Path
import pytest
from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_templates.loader import TemplateLoader
from src.narrative.subtext_templates.matcher import ContextMatcher


def test_context_matcher_emotion_and_power():
    loader = TemplateLoader()
    templates = list(loader.load_all().values())
    matcher = ContextMatcher()

    ctx = SubtextContext(
        emotion="betrayal",
        power_dynamic="inferior",
        relationship="former_ally",
    )
    matches = matcher.match(templates, ctx)
    assert len(matches) > 0
    # Highest match should be a betrayal template
    top = matches[0]
    assert "betrayal" in top.metadata.tags or top.metadata.category == "betrayal"


def test_context_matcher_deterministic_selection():
    loader = TemplateLoader()
    templates = list(loader.load_all().values())
    matcher = ContextMatcher()

    ctx = SubtextContext(scene_id="s1", turn_index=1, emotion="grief")
    sel1 = matcher.select(templates, ctx, seed=42)
    sel2 = matcher.select(templates, ctx, seed=42)
    assert sel1 is not None
    assert sel2 is not None
    assert sel1.id == sel2.id


def test_context_matcher_history_penalty():
    loader = TemplateLoader()
    templates = list(loader.load_all().values())
    matcher = ContextMatcher()

    ctx = SubtextContext(
        emotion="betrayal",
        history_summary=["betrayal.cold_acceptance"],
    )
    matches = matcher.match(templates, ctx)
    # The recent template should receive a score penalty
    for m in matches:
        if m.id == "betrayal.cold_acceptance":
            assert m.score < m.metadata.weight
