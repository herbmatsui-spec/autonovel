"""Unit tests for PredicateScorer."""

import pytest
from src.models.predicate_match import PredicateAnalysisResult, PredicateMatch
from src.services.nlp.predicate_scorer import PredicateScorer


def test_scorer_resolved_full_score():
    """Verify resolved predicate gives maximum 25 points."""
    match = PredicateMatch(
        keyword="聖剣",
        predicate="抜く",
        predicate_type="resolved",
        sentence="彼は台座から聖剣を抜いた。",
        confidence_score=1.0,
    )
    analysis = PredicateAnalysisResult(foreshadowing_id=1, matches=[match])
    assert PredicateScorer.calculate_score(analysis) == 25


def test_scorer_progressed_score():
    """Verify progressed predicate gives 15 points."""
    match = PredicateMatch(
        keyword="黒幕の影",
        predicate="気づく",
        predicate_type="progressed",
        sentence="主人公は背後に潜む黒幕の影に気づいた。",
        confidence_score=1.0,
    )
    analysis = PredicateAnalysisResult(foreshadowing_id=2, matches=[match])
    assert PredicateScorer.calculate_score(analysis) == 15


def test_scorer_mention_only_score():
    """Verify mention only gives 5 points."""
    match = PredicateMatch(
        keyword="指輪",
        predicate="見る",
        predicate_type="mention_only",
        sentence="彼は指輪を見た。",
        confidence_score=1.0,
    )
    analysis = PredicateAnalysisResult(foreshadowing_id=3, matches=[match])
    assert PredicateScorer.calculate_score(analysis) == 5


def test_scorer_negated_resolution_penalized_to_zero():
    """Verify negated resolution sentence does not grant resolution points."""
    match = PredicateMatch(
        keyword="秘密",
        predicate="解明する",
        predicate_type="resolved",
        sentence="古代の秘密は解明されなかった。",
        confidence_score=1.0,
    )
    analysis = PredicateAnalysisResult(foreshadowing_id=4, matches=[match])
    assert PredicateScorer.calculate_score(analysis) == 0


def test_scorer_confidence_scaling():
    """Verify lower confidence scales the score accordingly."""
    match = PredicateMatch(
        keyword="封印",
        predicate="解ける",
        predicate_type="resolved",
        sentence="封印が解けた。",
        confidence_score=0.8,
    )
    analysis = PredicateAnalysisResult(foreshadowing_id=5, matches=[match])
    # 25 * 0.8 = 20
    assert PredicateScorer.calculate_score(analysis) == 20
