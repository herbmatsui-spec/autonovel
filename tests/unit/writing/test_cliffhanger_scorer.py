"""
Unit tests for Cliffhanger Scorer.
PLAN 02 - Step 2: 話末クリフハンガー判定エンジンの単体テスト作成（TDD先行）
"""
from __future__ import annotations

import pytest
from src.models.opening_booster import CliffhangerType
from src.services.auditors.cliffhanger_scorer import score_cliffhanger


def test_score_cliffhanger_crisis():
    """危機直前での終了（命や立場の危機、急襲）の判定テスト"""
    text = "…その時、背後の扉が轟音と共に蹴り破られた。「見つけたぞ、裏切り者め」"
    result = score_cliffhanger(text)
    assert result.hook_type == CliffhangerType.CRISIS
    assert result.score >= 80.0
    assert result.requires_rewrite is False
    assert result.tail_sentence != ""


def test_score_cliffhanger_shocking_truth():
    """衝撃の事実・裏切りの判明の判定テスト"""
    text = "震える手で受け取った羊皮紙に記されていたのは、信頼していた師匠の署名と、俺を暗殺せよという冷酷な密命だった。"
    result = score_cliffhanger(text)
    assert result.hook_type == CliffhangerType.SHOCKING_TRUTH
    assert result.score >= 80.0
    assert result.requires_rewrite is False


def test_score_cliffhanger_triumph_trigger():
    """反撃・覚醒・ざまぁ直前トリガーの判定テスト"""
    text = "口元に冷笑を浮かべ、男は静かに呟いた。「そうか、これが貴様らの全力か。……ならば次は、こちらの番だな」"
    result = score_cliffhanger(text)
    assert result.hook_type == CliffhangerType.TRIUMPH_TRIGGER
    assert result.score >= 80.0
    assert result.requires_rewrite is False


def test_score_cliffhanger_peaceful_fails():
    """平穏・のんびり終了の失格・リライト判定テスト"""
    text = "今日も良い一日だった。主人公は温かいベッドに入り、静かに眠りについた。"
    result = score_cliffhanger(text)
    assert result.hook_type == CliffhangerType.PEACEFUL
    assert result.score < 50.0
    assert result.requires_rewrite is True
