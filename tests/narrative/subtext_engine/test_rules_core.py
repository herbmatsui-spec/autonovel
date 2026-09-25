"""
Unit tests for Core Rewrite Rules 1-7 (Steps 7-13).
"""

import pytest
from src.narrative.subtext_engine.models import DialogueBlock, SubtextContext
from src.narrative.subtext_engine.rules import (
    AddressDistanceRule,
    CausalToIronyRule,
    ComplianceSubvertRule,
    EmotionToActionRule,
    ExplanatoryCompressRule,
    SubjectiveInternalizeRule,
    ThreatSubtextRule,
)


def test_rule_01_explanatory_compress():
    rule = ExplanatoryCompressRule()
    # 3 consecutive dialogue lines
    block = DialogueBlock(
        speaker="説明キャラ",
        lines=[
            "「魔王軍が北の砦を占拠したらしい」",
            "「食糧補給線も完全に断たれてしまっている」",
            "「このままでは我々は冬を越せない」",
        ],
    )
    res = rule.apply(block)
    assert res.modified is True
    # Should keep last line and insert beat before it
    assert len(res.block.lines) == 2
    assert res.block.lines[0].startswith("（")
    assert res.block.lines[1] == "「このままでは我々は冬を越せない」"


def test_rule_02_emotion_to_action():
    rule = EmotionToActionRule()
    block = DialogueBlock(speaker="カイン", lines=["「私は悲しい」"])
    res = rule.apply(block)
    assert res.modified is True
    assert "悲しげな表情で" in res.block.raw_text()

    # Negation check: 悲しくない should not trigger
    block_neg = DialogueBlock(speaker="カイン", lines=["「別に悲しくない」"])
    res_neg = rule.apply(block_neg)
    assert res_neg.modified is False


def test_rule_03_causal_to_irony():
    rule = CausalToIronyRule()
    block = DialogueBlock(
        speaker="エドワード",
        lines=["「なぜなら君にはその資格がないからだ」"],
    )
    res = rule.apply(block)
    assert res.modified is True
    assert any(phrase in res.block.raw_text() for phrase in rule.irony_pool)


def test_rule_04_subjective_internalize():
    rule = SubjectiveInternalizeRule()
    block = DialogueBlock(
        speaker="クララ",
        lines=["「私は彼が犯人だと確信しています」"],
    )
    res = rule.apply(block)
    assert res.modified is True
    assert "（……" in res.block.lines[0]
    assert "確信しげな素振りを見せ" in res.block.lines[0]


def test_rule_05_threat_subtext():
    rule = ThreatSubtextRule()
    block = DialogueBlock(
        speaker="暗殺者",
        lines=["「絶対に殺してやる」"],
    )
    res = rule.apply(block)
    assert res.modified is True
    assert "——" in res.block.lines[0]
    assert any(phrase in res.block.lines[0] for phrase in rule.cold_phrases)


def test_rule_06_compliance_subvert():
    rule = ComplianceSubvertRule()
    block = DialogueBlock(speaker="部下", lines=["「はい」"])
    res = rule.apply(block, context=SubtextContext(turn_index=10))
    assert res.modified is True
    assert "「……仰せのままに" in res.block.lines[0] or "（無言のまま" in res.block.lines[0]


def test_rule_07_address_distance():
    rule = AddressDistanceRule()
    block = DialogueBlock(speaker="元親友", lines=["「お前、本当にそれでいいのか？」"])
    # With hostile context
    ctx = SubtextContext(relationship="enemy")
    res = rule.apply(block, context=ctx)
    assert res.modified is True
    assert "貴方" in res.block.lines[0]
