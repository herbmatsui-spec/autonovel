"""Unit and integration tests for Calibrated Audit Aggregator (Part 2 / Step 24 / Checkpoint 4)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.specialist_auditor_base import SpecialistAuditor, SpecialistAuditResult
from src.services.audit_aggregator import (
    AuditAggregator,
    BookScoreResult,
    SPECIALIST_NAMES,
)
from src.services.score_calibrator import ScoreCalibrator


def create_dummy_specialists(scores_map: dict[str, float]) -> list[SpecialistAuditor]:
    specialists = []
    for name in SPECIALIST_NAMES:
        s = MagicMock(spec=SpecialistAuditor)
        s.specialist_name = name
        score = scores_map.get(name, 65.0)
        res = SpecialistAuditResult(specialist_name=name, score=score, confidence=0.9)
        s._safe_audit = AsyncMock(return_value=res)
        specialists.append(s)
    return specialists


@pytest.mark.asyncio
async def test_audit_aggregator_calibration_integration():
    """Verify AuditAggregator runs calibration and sets calibrated fields in BookScoreResult."""
    # Equal weights for all 8 specialists
    eq_w = {n: 0.125 for n in SPECIALIST_NAMES}
    scores_map = {n: 65.0 for n in SPECIALIST_NAMES}
    specialists = create_dummy_specialists(scores_map)

    agg = AuditAggregator(specialists=specialists, weights=eq_w)
    assert agg.calibrator is not None

    await agg.run_all({"draft_text": "テストテキスト"})
    res = agg.aggregate(genre="general", apply_calibration=True)

    assert isinstance(res, BookScoreResult)
    assert res.calibrated_overall is not None
    assert len(res.calibrated_by_specialist) == 8
    assert len(res.calibration_meta) == 8
    # All scores near 65 -> calibrated should also be near 65
    assert 60.0 <= res.calibrated_overall <= 70.0


@pytest.mark.asyncio
async def test_audit_aggregator_outlier_detection():
    """Verify outliers are captured when an auditor gives an extreme score."""
    eq_w = {n: 0.125 for n in SPECIALIST_NAMES}
    # consistency prior mean is 70, std is 10. Raw score 20 is z = -5.0 (outlier)
    scores_map = {n: 70.0 for n in SPECIALIST_NAMES}
    scores_map["consistency"] = 20.0
    specialists = create_dummy_specialists(scores_map)

    agg = AuditAggregator(specialists=specialists, weights=eq_w)
    await agg.run_all({})
    res = agg.aggregate(genre="general", apply_calibration=True)

    assert "consistency" in res.outliers
    assert res.to_dict()["outliers"] == ["consistency"]


@pytest.mark.asyncio
async def test_audit_aggregator_variance_penalty():
    """High score variance across specialists should trigger a variance penalty."""
    eq_w = {n: 0.125 for n in SPECIALIST_NAMES}
    # Extremely polarized scores across specialists
    scores_map = {
        "reader_hook": 95.0,
        "consistency": 30.0,
        "structure": 90.0,
        "emotion_curve": 35.0,
        "style": 95.0,
        "factual": 30.0,
        "creativity": 95.0,
        "multimodal": 35.0,
    }
    specialists = create_dummy_specialists(scores_map)

    agg = AuditAggregator(specialists=specialists, weights=eq_w)
    await agg.run_all({})
    res = agg.aggregate(genre="general", apply_calibration=True)

    assert res.variance_penalty > 0.0
    # calibrated_overall should reflect penalty deduction
    raw_calibrated_sum = sum(res.calibrated_by_specialist[n] * eq_w[n] for n in SPECIALIST_NAMES)
    assert res.calibrated_overall < raw_calibrated_sum


@pytest.mark.asyncio
async def test_lowest_dimension_with_calibration():
    """Verify lowest_dimension accurately picks the calibrated minimum."""
    eq_w = {n: 0.125 for n in SPECIALIST_NAMES}
    scores_map = {n: 70.0 for n in SPECIALIST_NAMES}
    # Set emotion_curve raw score low
    scores_map["emotion_curve"] = 40.0
    specialists = create_dummy_specialists(scores_map)

    agg = AuditAggregator(specialists=specialists, weights=eq_w)
    await agg.run_all({})
    res = agg.aggregate(genre="romance", apply_calibration=True)

    assert res.lowest_dimension(use_calibrated=True) == "emotion_curve"


@pytest.mark.asyncio
async def test_publish_aggregated_metrics_includes_calibration():
    """Verify publish_aggregated_metrics sends calibrated scores and penalty to event_bus."""
    mock_bus = MagicMock()
    mock_bus.publish_async = AsyncMock()

    eq_w = {n: 0.125 for n in SPECIALIST_NAMES}
    scores_map = {n: 65.0 for n in SPECIALIST_NAMES}
    specialists = create_dummy_specialists(scores_map)

    agg = AuditAggregator(specialists=specialists, weights=eq_w, event_bus=mock_bus)
    await agg.run_all({})
    res = agg.aggregate(genre="fantasy")

    await agg.publish_aggregated_metrics(res, ctx={"genre": "fantasy", "book_id": "b1"})
    assert mock_bus.publish_async.called
    call_payload = mock_bus.publish_async.call_args[0][0].payload
    assert "calibrated_overall_score" in call_payload
    assert "calibrated_specialist_scores" in call_payload
    assert "variance_penalty" in call_payload
    assert "outliers" in call_payload
