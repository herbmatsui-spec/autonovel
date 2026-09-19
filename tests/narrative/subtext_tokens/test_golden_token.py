"""
Golden sample regression test suite for Subtext Token Expansion (PLAN_Y3 Step 17).
Executes all 40 golden samples from tests/golden/token_expansion/.
"""

import json
from pathlib import Path
import pytest
from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_tokens.formatter import DialogueFormatter

GOLDEN_DIR = Path("tests/golden/token_expansion")


def pytest_generate_tests(metafunc):
    if "golden_file" in metafunc.fixturenames:
        files = sorted(GOLDEN_DIR.glob("*.json"))
        metafunc.parametrize("golden_file", files, ids=[f.stem for f in files])


def test_golden_token_expansion(golden_file):
    with open(golden_file, "r", encoding="utf-8") as f:
        case = json.load(f)

    formatter = DialogueFormatter()
    raw = case["raw"]
    processed = formatter.post_process_dialogue(raw, seed=123)

    # Check that control tokens were expanded and removed
    for not_exp in case.get("expected_not_contains", []):
        assert not_exp not in processed, f"Token {not_exp} was not expanded in:\n{processed}"

    # Check that expected strings exist in processed text
    for exp in case.get("expected_contains", []):
        assert exp in processed, f"Case {case['id']} expected '{exp}' in output:\n{processed}"

    expected_any = case.get("expected_any", [])
    if expected_any:
        assert any(exp in processed for exp in expected_any), (
            f"Case {case['id']} expected at least one of {expected_any} in output:\n{processed}"
        )
