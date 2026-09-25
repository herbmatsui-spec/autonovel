"""
Unit tests for core template categories (PLAN_Y2 Step 7-12).
Tests rendering across betrayal, grief, power_play, romance, comedy, and action.
"""

import pytest
from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_templates.loader import TemplateLoader
from src.narrative.subtext_templates.renderer import TemplateRenderer


@pytest.fixture
def renderer():
    return TemplateRenderer()


def test_betrayal_templates(renderer):
    templates = [
        "betrayal.cold_acceptance",
        "betrayal.masked_rage",
        "betrayal.quiet_threat",
        "betrayal.false_forgiveness",
        "betrayal.calculated_retreat",
    ]
    for tid in templates:
        res = renderer.render(tid)
        assert res.template_id == tid
        assert len(res.lines) >= 1
        assert len(res.raw_text.strip()) > 0


def test_grief_templates(renderer):
    templates = [
        "grief.denial_through_action",
        "grief.suppressed_tears",
        "grief.quiet_breakdown",
        "grief.stoic_endurance",
    ]
    for tid in templates:
        res = renderer.render(tid)
        assert res.template_id == tid
        assert len(res.lines) >= 1


def test_power_play_templates(renderer):
    templates = [
        "power_play.ironic_politeness",
        "power_play.silence_as_weapon",
        "power_play.feigned_ignorance",
        "power_play.conditional_compliance",
    ]
    for tid in templates:
        res = renderer.render(tid)
        assert res.template_id == tid


def test_romance_templates(renderer):
    templates = [
        "romance.masked_longing",
        "romance.deflected_confession",
        "romance.teasing_as_shield",
        "romance.silent_understanding",
    ]
    for tid in templates:
        res = renderer.render(tid)
        assert res.template_id == tid


def test_comedy_templates(renderer):
    templates = [
        "comedy.self_deprecating_deflection",
        "comedy.absurdist_redirect",
        "comedy.deadpan_evade",
    ]
    for tid in templates:
        res = renderer.render(tid)
        assert res.template_id == tid


def test_action_templates(renderer):
    templates = [
        "action.meaningful_glance",
        "action.symbolic_gesture",
        "action.environmental_interaction",
    ]
    for tid in templates:
        res = renderer.render(tid)
        assert res.template_id == tid
        # Action templates should produce beats/actions
        assert any(l.type in ["beat", "action"] for l in res.lines)
