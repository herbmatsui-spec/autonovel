"""Unit tests for ForeshadowingPredicateAnalyzer classifying incidental mentions as mention_only."""

import pytest
from src.services.nlp.foreshadowing_predicate_analyzer import ForeshadowingPredicateAnalyzer


def test_mention_only_predicates_classification():
    """Verify analyzer classifies everyday actions as mention_only and prevents false resolution."""
    analyzer = ForeshadowingPredicateAnalyzer()

    # Case 1: 持っていた (held / possessed)
    text1 = "彼は古い懐中時計をポケットに持っていた。"
    res1 = analyzer.analyze_foreshadowing(1, ["懐中時計"], text1)
    assert res1.highest_action == "mention_only"
    assert res1.syntax_score == 5

    # Case 2: 見た / 眺めた (looked / observed)
    text2 = "少女は遠くの廃城を静かに眺めた。"
    res2 = analyzer.analyze_foreshadowing(2, ["廃城"], text2)
    assert res2.highest_action == "mention_only"
    assert res2.syntax_score == 5

    # Case 3: 話した (talked)
    text3 = "酒場で男たちは伝説の竜について楽しく話した。"
    res3 = analyzer.analyze_foreshadowing(3, ["竜"], text3)
    assert res3.highest_action == "mention_only"
    assert res3.syntax_score == 5
