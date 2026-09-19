"""
Unit tests for Jinja2 environment custom filters and macros (PLAN_Y2 Step 5).
"""

import pytest
from src.narrative.subtext_templates.renderer import TemplateRenderer


def test_custom_filters():
    renderer = TemplateRenderer()
    env = renderer.jinja_env

    # beat filter
    tmpl_beat = env.from_string("{{ '沈黙が流れる' | beat }}")
    assert tmpl_beat.render() == "（沈黙が流れる）"

    # action filter
    tmpl_action = env.from_string("{{ '視線を逸らした' | action }}")
    assert tmpl_action.render() == "——視線を逸らした。"

    # irony filter
    tmpl_irony = env.from_string("{{ '好きにすればいい' | irony }}")
    assert tmpl_irony.render() == "「……好きにすればいい」"
