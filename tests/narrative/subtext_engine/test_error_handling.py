"""
Unit tests for Error Handling & Fallback (Step 19).
"""

import pytest
from src.narrative.subtext_engine.engine import SubtextEngine
from src.narrative.subtext_engine.models import DialogueBlock
from src.narrative.subtext_engine.rules import RuleBase, RuleRegistry


class BuggyRule(RuleBase):
    def __init__(self):
        super().__init__(rule_id="buggy_rule", priority=5)

    def apply(self, block, context=None):
        raise RuntimeError("Simulated rule failure!")


def test_engine_graceful_fallback_on_rule_exception():
    registry = RuleRegistry()
    registry.register(BuggyRule())
    engine = SubtextEngine(registry=registry)

    original_lines = ["「こんにちは」", "「いい天気ですね」"]
    block = DialogueBlock(speaker="A", lines=list(original_lines))

    # Processing should NOT raise, should keep original text intact
    result_blocks = engine.process([block])
    assert len(result_blocks) == 1
    assert result_blocks[0].lines == original_lines
    assert result_blocks[0].applied_rules == []
