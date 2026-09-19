"""
Unit tests for shared data, constraints, stats, and i18n (PLAN_Y2 Step 13, 16, 22, 23).
"""

from pathlib import Path
import pytest
from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_templates.constraints import CharacterConstraints
from src.narrative.subtext_templates.loader import TemplateLoader
from src.narrative.subtext_templates.renderer import TemplateRenderer


def test_shared_vocabularies():
    renderer = TemplateRenderer()
    shared = renderer.shared_data
    assert "beats" in shared
    assert "actions" in shared
    assert "irony_phrases" in shared
    assert "pause" in shared["beats"]


def test_character_constraints():
    constraints = CharacterConstraints()
    # Elena forbids vulgar tags
    assert constraints.is_template_allowed("elena", ["vulgar"]) is False
    assert constraints.is_template_allowed("elena", ["betrayal", "cold"]) is True

    # Elena speech pattern substitution
    converted = constraints.apply_speech_patterns("elena", "そうだよ。だね")
    assert "ですわ" in converted


def test_i18n_templates():
    loader = TemplateLoader()
    en_tmpl = loader.parse_template_file(Path("templates/subtext/en/betrayal/cold_acceptance.j2"))
    assert en_tmpl is not None
    assert en_tmpl.id == "en.betrayal.cold_acceptance"

    renderer = TemplateRenderer()
    res_en = renderer.render(en_tmpl)
    assert "As you wish" in res_en.raw_text

    zh_tmpl = loader.parse_template_file(Path("templates/subtext/zh/betrayal/cold_acceptance.j2"))
    assert zh_tmpl is not None
    res_zh = renderer.render(zh_tmpl)
    assert "那就如你所愿吧" in res_zh.raw_text
