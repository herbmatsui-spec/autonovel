"""
Golden sample regression test suite for SubtextEngine (Step 17).
Executes all 30+ golden samples from tests/golden/subtext_before_after/.
"""

import json
from pathlib import Path
import pytest
from src.narrative.subtext_engine.engine import SubtextEngine
from src.narrative.subtext_engine.models import DialogueBlock, SubtextContext

GOLDEN_DIR = Path("tests/golden/subtext_before_after")


def pytest_generate_tests(metafunc):
    if "golden_file" in metafunc.fixturenames:
        files = sorted(GOLDEN_DIR.glob("*.json"))
        metafunc.parametrize("golden_file", files, ids=[f.stem for f in files])


def test_golden_sample_regression(golden_file):
    with open(golden_file, "r", encoding="utf-8") as f:
        case = json.load(f)

    engine = SubtextEngine.create_default()
    ctx_data = case.get("context", {})
    context = SubtextContext(**ctx_data) if ctx_data else None

    block = DialogueBlock(speaker=case.get("speaker", ""), lines=case["before"])
    results = engine.process([block], context=context)
    processed_block = results[0]

    # Verify expected content
    raw_output = processed_block.raw_text()
    expected_matches = case.get("expected_contains", [])
    for exp in expected_matches:
        assert exp in raw_output, f"Case {case['id']} expected '{exp}' in output:\n{raw_output}"

    expected_any = case.get("expected_any", [])
    if expected_any:
        assert any(item in raw_output for item in expected_any), (
            f"Case {case['id']} expected at least one of {expected_any} in output:\n{raw_output}"
        )

    # Verify applied rules if specified
    expected_rules = case.get("applied_rules")
    if expected_rules is not None:
        assert set(processed_block.applied_rules) == set(expected_rules), (
            f"Case {case['id']} rule mismatch: got {processed_block.applied_rules}, expected {expected_rules}"
        )
