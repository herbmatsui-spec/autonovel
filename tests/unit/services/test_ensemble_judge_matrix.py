"""Unit tests for EnsembleJudge matrix combinations."""

import pytest
from src.models.predicate_match import PredicateAnalysisResult, PredicateMatch
from src.models.writing_metadata import ForeshadowingReport
from src.services.foreshadowing.ensemble_judge import EnsembleJudge


def test_full_consensus_resolved():
    """Verify 100-point full consensus yields RESOLVED with no rescheduling."""
    report = ForeshadowingReport(foreshadowing_id=1, action="resolved")
    match = PredicateMatch(
        keyword="宝箱",
        predicate="開ける",
        predicate_type="resolved",
        sentence="宝箱を開けた。",
    )
    syntax = PredicateAnalysisResult(foreshadowing_id=1, matches=[match])

    judgment = EnsembleJudge.evaluate(
        foreshadowing_id=1,
        is_contracted=True,
        metadata_report=report,
        syntax_analysis=syntax,
    )

    assert judgment.status == "RESOLVED"
    assert judgment.score_breakdown.total_score == 100
    assert not judgment.should_reschedule


def test_contract_and_metadata_resolved_without_syntax():
    """Verify 75 points (Contract + Metadata) reaches RESOLVED threshold even if syntax failed."""
    report = ForeshadowingReport(foreshadowing_id=2, action="resolved")

    judgment = EnsembleJudge.evaluate(
        foreshadowing_id=2,
        is_contracted=True,
        metadata_report=report,
        syntax_analysis=None,
    )

    assert judgment.status == "RESOLVED"
    assert judgment.score_breakdown.total_score == 75
    assert not judgment.should_reschedule


def test_accidental_keyword_mention_prevented_from_false_resolution():
    """CRITICAL TEST: Verify pure syntax or accidental keyword match (25 pts max) NEVER falsely resolves."""
    # Accidental mention where neither contract nor metadata agrees
    match = PredicateMatch(
        keyword="手紙",
        predicate="明かす",
        predicate_type="resolved",
        sentence="彼は手紙を明かした。",
    )
    syntax = PredicateAnalysisResult(foreshadowing_id=3, matches=[match])

    judgment = EnsembleJudge.evaluate(
        foreshadowing_id=3,
        is_contracted=False,  # Not in beat contract
        metadata_report=None,  # No LLM self-report
        syntax_analysis=syntax,  # 25 points only
    )

    # Even with resolved predicate (25 pts), without contract and metadata it must NEVER resolve
    assert judgment.status != "RESOLVED"
    assert judgment.status == "PROGRESSED"  # Progressed without contract
    assert judgment.score_breakdown.total_score == 25

    # Case where mention is everyday action (syntax = 5 pts)
    match_everyday = PredicateMatch(
        keyword="手紙",
        predicate="見る",
        predicate_type="mention_only",
        sentence="彼は手紙を見た。",
    )
    syntax_everyday = PredicateAnalysisResult(foreshadowing_id=3, matches=[match_everyday])
    judgment_everyday = EnsembleJudge.evaluate(
        foreshadowing_id=3,
        is_contracted=False,
        metadata_report=None,
        syntax_analysis=syntax_everyday,
    )
    assert judgment_everyday.status == "PLANTED"
    assert not judgment_everyday.should_reschedule


def test_progressed_status_and_rescheduling():
    """Verify 55 points (Contract + progressed metadata) sets PROGRESSED and marks for rescheduling."""
    report = ForeshadowingReport(foreshadowing_id=4, action="progressed")

    judgment = EnsembleJudge.evaluate(
        foreshadowing_id=4,
        is_contracted=True,  # 35
        metadata_report=report,  # 20
        syntax_analysis=None,  # 0
    )

    assert judgment.status == "PROGRESSED"
    assert judgment.score_breakdown.total_score == 55
    assert judgment.should_reschedule is True
