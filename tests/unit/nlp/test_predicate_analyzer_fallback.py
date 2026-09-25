"""Unit tests for ForeshadowingPredicateAnalyzer fallback mechanisms."""

import pytest
from src.services.nlp.foreshadowing_predicate_analyzer import ForeshadowingPredicateAnalyzer


def test_fallback_when_tokenizer_disabled():
    """Verify analyzer functions accurately via regex dictionary fallback even without Sudachi."""
    analyzer = ForeshadowingPredicateAnalyzer()
    analyzer._tokenizer = None  # Simulate environment where Sudachi tokenizer failed to initialize

    # Test resolution with fallback
    text_res = "その事件の真相が解明された。"
    res1 = analyzer.analyze_foreshadowing(1, ["真相"], text_res)
    assert res1.highest_action == "resolved"
    assert res1.syntax_score == 25
    assert res1.matches[0].confidence_score == 0.7  # Fallback confidence

    # Test mention only with fallback
    text_mention = "彼らは机の上の地図を見た。"
    res2 = analyzer.analyze_foreshadowing(2, ["地図"], text_mention)
    assert res2.highest_action == "mention_only"
    assert res2.syntax_score == 5


def test_keyword_not_in_text():
    """Verify analyzer returns none when keyword is absent."""
    analyzer = ForeshadowingPredicateAnalyzer()
    text = "穏やかな朝の光が差し込んでいた。"
    res = analyzer.analyze_foreshadowing(1, ["魔王の封印"], text)
    assert res.highest_action == "none"
    assert res.syntax_score == 0
    assert len(res.matches) == 0
