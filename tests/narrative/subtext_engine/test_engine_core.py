"""
Unit tests for SubtextEngine core processing (Step 5).
"""

import pytest
from src.narrative.subtext_engine.engine import SubtextEngine
from src.narrative.subtext_engine.models import DialogueBlock, SubtextContext
from src.narrative.subtext_engine.rules import RegexRule, RuleRegistry


def test_engine_processes_rules_in_priority_order():
    registry = RuleRegistry()
    # rule 1 adds suffix A
    r1 = RegexRule(
        rule_id="r1",
        pattern=r"START",
        replacement="START_A",
        priority=10,
    )
    # rule 2 adds suffix B to A
    r2 = RegexRule(
        rule_id="r2",
        pattern=r"START_A",
        replacement="START_AB",
        priority=20,
    )
    registry.register(r2)
    registry.register(r1)

    engine = SubtextEngine(registry=registry)
    blocks = [DialogueBlock(speaker="X", lines=["START"])]
    res = engine.process(blocks)

    assert res[0].lines == ["START_AB"]
    assert res[0].applied_rules == ["r1", "r2"]


def test_engine_final_flag_stops_subsequent_rules():
    registry = RuleRegistry()
    r1 = RegexRule(
        rule_id="r_final",
        pattern=r"STOP",
        replacement="STOPPED",
        priority=10,
        final=True,
    )
    r2 = RegexRule(
        rule_id="r_after",
        pattern=r"STOPPED",
        replacement="SHOULD_NOT_EXECUTE",
        priority=20,
    )
    registry.register(r1)
    registry.register(r2)

    engine = SubtextEngine(registry=registry)
    blocks = [DialogueBlock(speaker="Y", lines=["STOP"])]
    res = engine.process(blocks)

    assert res[0].lines == ["STOPPED"]
    assert res[0].applied_rules == ["r_final"]


def test_engine_report_generation():
    engine = SubtextEngine.create_default()
    blocks = [
        DialogueBlock(speaker="A", lines=["「はい」"]),
        DialogueBlock(speaker="B", lines=["「私は悲しい」"]),
    ]
    engine.process(blocks)
    report = engine.generate_report()

    assert report["total_blocks_processed"] == 2
    assert report["modified_blocks_count"] >= 1
    assert "rule_application_counts" in report
