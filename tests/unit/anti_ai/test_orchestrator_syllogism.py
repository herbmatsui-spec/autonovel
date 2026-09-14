"""
Unit tests for RuleBasedAntiAIDetector with EmotionSyllogismDetector integration.
PLAN 03 - Step 10: 総合スコア計算への三段論法ペナルティ統合検証
"""
from __future__ import annotations

import pytest
from src.services.anti_ai.models import AICategory
from src.services.anti_ai.orchestrator import RuleBasedAntiAIDetector


def test_orchestrator_detects_emotion_syllogism():
    """オーケストレーターが三段論法構文を検知し、EMOTION_SYLLOGISMスコアと総合スコアを減点すること"""
    detector = RuleBasedAntiAIDetector()
    text = (
        "彼は怒りを感じた。なぜなら仲間を侮辱されたからだ。"
        "しかし、耐えるべきだと自分に言い聞かせた。"
    )
    result = detector.detect(text)

    # EMOTION_SYLLOGISM が violations に含まれていること
    syllogism_hits = [v for v in result.violations if v.category == AICategory.EMOTION_SYLLOGISM]
    assert len(syllogism_hits) >= 1

    # カテゴリスコアおよび総合スコアが100点満点から減点されていること
    assert result.category_scores[AICategory.EMOTION_SYLLOGISM] < 100.0
    assert result.total_score < 100.0


def test_orchestrator_clean_text_gets_high_score():
    """三段論法やAI構文のない生々しい文章が高スコアを獲得すること"""
    detector = RuleBasedAntiAIDetector()
    text = (
        "男の侮辱に、アルトは奥歯を強く噛み締めた。"
        "『今に見ろ、後悔させてやる』――冷たい笑みが口元に浮かんだ。"
    )
    result = detector.detect(text)
    assert result.category_scores[AICategory.EMOTION_SYLLOGISM] == 100.0
