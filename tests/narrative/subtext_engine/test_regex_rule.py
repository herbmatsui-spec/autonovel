"""
Unit tests for RegexRule (Step 4).
"""

import pytest
from src.narrative.subtext_engine.models import DialogueBlock
from src.narrative.subtext_engine.rules import RegexRule


def test_regex_rule_string_replacement():
    rule = RegexRule(
        rule_id="test_replace",
        pattern=r"「マジで？」",
        replacement=r"「本気なのか……？」",
        priority=10,
    )
    block = DialogueBlock(speaker="アリス", lines=["「マジで？」", "信じられない。"])
    res = rule.apply(block)

    assert res.modified is True
    assert res.block.lines[0] == "「本気なのか……？」"
    assert "test_replace" in res.block.applied_rules


def test_regex_rule_callable_replacement():
    def custom_sub(match):
        return f"【{match.group(1)}】"

    rule = RegexRule(
        rule_id="test_callable",
        pattern=r"<target>(.+?)</target>",
        replacement=custom_sub,
    )
    block = DialogueBlock(speaker="ボブ", lines=["ここに<target>重要機密</target>がある。"])
    res = rule.apply(block)

    assert res.modified is True
    assert res.block.lines[0] == "ここに【重要機密】がある。"


def test_regex_rule_skip_if_matched():
    rule = RegexRule(
        rule_id="test_skip",
        pattern=r"apple",
        replacement="orange",
        skip_if_matched=True,
    )
    block = DialogueBlock(
        speaker="C",
        lines=["apple"],
        applied_rules=["test_skip"],
    )
    res = rule.apply(block)
    assert res.modified is False
    assert res.block.lines == ["apple"]
