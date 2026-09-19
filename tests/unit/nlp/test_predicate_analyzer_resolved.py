"""Unit tests for ForeshadowingPredicateAnalyzer detecting resolved predicates."""

import pytest
from src.services.nlp.foreshadowing_predicate_analyzer import ForeshadowingPredicateAnalyzer


def test_resolved_predicates_detection():
    """Verify analyzer identifies resolution predicates accurately."""
    analyzer = ForeshadowingPredicateAnalyzer()

    # Case 1: 明かす (reveal)
    text1 = "探偵はその手紙の秘密を明かした。"
    res1 = analyzer.analyze_foreshadowing(1, ["手紙"], text1)
    assert res1.highest_action == "resolved"
    assert res1.syntax_score == 25
    assert any(m.predicate_type == "resolved" for m in res1.matches)

    # Case 2: 砕け散る (shatter / complete)
    text2 = "古びたペンダントが砕け散った。"
    res2 = analyzer.analyze_foreshadowing(2, ["ペンダント"], text2)
    assert res2.highest_action == "resolved"
    assert res2.syntax_score == 25

    # Case 3: 解明される (solved)
    text3 = "古代遺跡の謎がついに解明された。"
    res3 = analyzer.analyze_foreshadowing(3, ["謎"], text3)
    assert res3.highest_action == "resolved"
    assert res3.syntax_score == 25
