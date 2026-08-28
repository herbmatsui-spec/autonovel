"""
tests/unit/test_narrative_adapters.py - Phase 2: アダプタ群の単体テスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.backend.workflows.narrative_state import NarrativeState
from src.backend.workflows.adapters.tension_adapter import update_tension
from src.backend.workflows.adapters.affinity_adapter import update_affinity
from src.backend.workflows.adapters.quality_adapter import update_quality
from src.backend.workflows.adapters.narrative_adapter import update_narrative
from src.backend.workflows.adapters.erotic_adapter import update_erotic
from src.backend.workflows.adapters.continuity_adapter import feed_continuity


@pytest.mark.asyncio
async def test_update_tension():
    """ステップ 8: テンションアダプタのテスト"""
    hub = NarrativeState()
    await update_tension(hub, 1, 0.75)
    await update_tension(hub, 2, 0.85)

    assert hub.tension_curve == [0.75, 0.85]
    assert hub.episodes[1]["tension"] == 0.75
    assert hub.episodes[2]["tension"] == 0.85


def test_update_affinity():
    """ステップ 9: 好感度アダプタのテスト"""
    hub = NarrativeState()
    mock_tracker = MagicMock()
    mock_data1 = MagicMock()
    mock_data1.character_name = "メインヒロイン"
    mock_data1.affinity_score = 65.0
    mock_tracker.update_from_text.return_value = [mock_data1]

    update_affinity(hub, 1, "ありがとう、嬉しいです！", tracker=mock_tracker)

    assert hub.affinity_map == {"メインヒロイン": 65.0}
    assert hub.episodes[1]["affinity"] == {"メインヒロイン": 65.0}


@pytest.mark.asyncio
async def test_update_quality():
    """ステップ 10: 品質スコアアダプタのテスト"""
    hub = NarrativeState()
    mock_scorer = MagicMock()
    mock_report = MagicMock()
    mock_report.__dict__ = {
        "coherence_score": 0.9,
        "character_consistency": 0.85,
        "pacing_score": 0.8,
        "hook_retention": 0.75,
        "emotional_resonance": 0.88,
        "commercial_viability": 0.82,
    }
    mock_scorer.score_all = AsyncMock(return_value=mock_report)

    res = await update_quality(hub, 1, "テスト小説本文", scorer=mock_scorer)

    assert hub.quality_scores[1]["coherence_score"] == 0.9
    assert hub.episodes[1]["quality"]["character_consistency"] == 0.85
    assert res["pacing_score"] == 0.8


@pytest.mark.asyncio
async def test_update_narrative():
    """ステップ 11: ナラティブスコアアダプタのテスト"""
    hub = NarrativeState()
    mock_service = MagicMock()
    mock_service.score = AsyncMock(return_value={"overall_narrative_score": 92.5, "feedback": "Excellent"})

    res = await update_narrative(hub, 1, "テスト本文", service=mock_service)

    assert hub.narrative_scores[1]["overall_narrative_score"] == 92.5
    assert hub.episodes[1]["narrative"]["feedback"] == "Excellent"
    assert res["overall_narrative_score"] == 92.5


def test_update_erotic():
    """ステップ 12: 官能品質アダプタのテスト"""
    hub = NarrativeState()
    mock_scorer = MagicMock()
    mock_report = MagicMock()
    mock_report.overall_score = 88.0
    mock_report.sensuality_score = 85.0
    mock_report.emotional_score = 90.0
    mock_report.psychological_score = 80.0
    mock_report.technical_score = 85.0
    mock_scorer.score.return_value = mock_report

    res = update_erotic(hub, 1, "甘く吐息が漏れるシーン", scorer=mock_scorer)

    assert hub.erotic_metrics[1]["overall_score"] == 88.0
    assert hub.erotic_metrics[1]["sensuality_score"] == 85.0
    assert hub.episodes[1]["erotic"]["overall_score"] == 88.0
    assert res["overall_score"] == 88.0


def test_feed_continuity():
    """ステップ 13: 連続性アダプタのテスト"""
    hub = NarrativeState()
    mock_tracker = MagicMock()
    mock_tracker.feed.return_value = [{"field": "hp", "msg": "HP cannot increase without healing"}]

    v = feed_continuity(hub, {"ep": 2, "character": "Hero", "hp": 100}, tracker=mock_tracker)

    assert len(hub.continuity_violations) == 1
    assert hub.continuity_violations[0]["field"] == "hp"
    assert hub.episodes[2]["continuity_violations"] == [{"field": "hp", "msg": "HP cannot increase without healing"}]
    assert v == [{"field": "hp", "msg": "HP cannot increase without healing"}]
