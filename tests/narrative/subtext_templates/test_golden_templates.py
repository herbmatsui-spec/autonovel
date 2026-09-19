"""
Golden sample regression test suite for Subtext Template Library (PLAN_Y2 Step 21).
Executes all 50 golden samples from tests/golden/templates/.
"""

import json
from pathlib import Path
import pytest
from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_templates.loader import TemplateLoader
from src.narrative.subtext_templates.matcher import ContextMatcher
from src.narrative.subtext_templates.renderer import TemplateRenderer

GOLDEN_DIR = Path("tests/golden/templates")


def pytest_generate_tests(metafunc):
    if "golden_file" in metafunc.fixturenames:
        files = sorted(GOLDEN_DIR.glob("*.json"))
        metafunc.parametrize("golden_file", files, ids=[f.stem for f in files])


def test_golden_template_selection_and_rendering(golden_file):
    with open(golden_file, "r", encoding="utf-8") as f:
        case = json.load(f)

    loader = TemplateLoader()
    matcher = ContextMatcher()
    renderer = TemplateRenderer(loader=loader)

    ctx = SubtextContext(**case["context"])
    templates = list(loader.load_all().values())
    matches = matcher.match(templates, ctx)

    assert len(matches) > 0, f"No template matches for case {case['id']}"
    selected = matcher.select(matches, ctx, seed=case["context"]["turn_index"])
    assert selected is not None, f"Selection failed for case {case['id']}"

    # Verify category match or appropriate subtext category
    meta = selected.metadata
    cat = meta.category or meta.id.split(".")[0]
    expected_cat = case["expected_category"]
    assert cat == expected_cat or expected_cat in meta.tags or "fallback" in cat, (
        f"Case {case['id']} expected category {expected_cat}, got {cat}"
    )

    # Verify rendering produces valid dialogue/beats
    rendered = renderer.render(selected, context=ctx)
    assert len(rendered.lines) >= 1
    assert len(rendered.raw_text.strip()) > 0
