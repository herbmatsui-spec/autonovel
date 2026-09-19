"""
Unit tests for Conflict Detection (Step 21).
"""

import pytest
from src.narrative.subtext_engine.engine import SubtextEngine
from src.narrative.subtext_engine.models import DialogueBlock
from src.narrative.subtext_engine.rules import RegexRule, RuleRegistry


def test_conflict_detection_multiple_matching_rules():
    registry = RuleRegistry()
    r1 = RegexRule(rule_id="rule_one", pattern=r"TARGET", replacement="ONE")
    r2 = RegexRule(rule_id="rule_two", pattern=r"TARGET", replacement="TWO")
    registry.register(r1)
    registry.register(r2)

    engine = SubtextEngine(registry=registry)
    sample_blocks = [
        DialogueBlock(speaker="A", lines=["Here is TARGET word."]),
        DialogueBlock(speaker="B", lines=["No conflict here."]),
    ]
    conflicts = engine.detect_conflicts(sample_blocks)

    assert len(conflicts) == 1
    assert conflicts[0]["speaker"] == "A"
    assert set(conflicts[0]["matching_rules"]) == {"rule_one", "rule_two"}
