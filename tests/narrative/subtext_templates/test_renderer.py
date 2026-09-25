"""
Unit tests for TemplateRenderer and fallback chain (PLAN_Y2 Step 6, 18).
"""

import pytest
from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_templates.renderer import TemplateRenderer


def test_render_existing_template():
    renderer = TemplateRenderer()
    ctx = SubtextContext(speaker="エレン", emotion="betrayal")
    res = renderer.render("betrayal.cold_acceptance", context=ctx)

    assert res.template_id == "betrayal.cold_acceptance"
    assert len(res.lines) >= 2
    assert "……" in res.raw_text
    assert any(line.type == "action" for line in res.lines)


def test_render_fallback_chain_on_missing_template():
    renderer = TemplateRenderer()
    ctx = SubtextContext(speaker="カイン")
    # Non-existent template should trigger fallback
    res = renderer.render("completely.nonexistent.template.id", context=ctx)

    assert res.template_id in ["fallback.generic_subtext", "fallback.minimal_beat", "hardcoded_fallback"]
    assert len(res.lines) > 0
