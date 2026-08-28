"""
tests/unit/test_prototype_score.py - ステップ 5: PrototypeScorer の単体テスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.prototype.score_adapter import PrototypeScorer
from novel_50ep.score_reviewer import EpisodeScore


@pytest.mark.asyncio
async def test_prototype_scorer_async():
    """モックサービスを用いたスコアリングテスト"""
    mock_quality = MagicMock()
    mock_q_rep = MagicMock()
    mock_q_rep.pacing_score = 0.9
    mock_q_rep.emotional_resonance = 0.85
    mock_q_rep.coherence_score = 0.95
    mock_q_rep.hook_retention = 0.8
    mock_quality.score_all = AsyncMock(return_value=mock_q_rep)

    mock_narrative = MagicMock()
    mock_narrative.score = AsyncMock(return_value={"overall_narrative_score": 90.0})

    scorer = PrototypeScorer(quality_scorer=mock_quality, narrative_scorer=mock_narrative)
    res = await scorer.score(1, "テストエピソード本文")

    assert isinstance(res, EpisodeScore)
    assert res.ep == 1
    assert res.pacing_score == 0.9
    assert res.emotion_score == 0.85
    assert res.world_score == 0.95
    assert res.cliff_score == 0.8
    assert res.total_score > 0.0
    assert "narrative" in res.details


def test_prototype_scorer_sync():
    """同期インターフェース呼び出しテスト"""
    mock_quality = MagicMock()
    mock_q_rep = MagicMock()
    mock_q_rep.pacing_score = 0.8
    mock_q_rep.emotional_resonance = 0.8
    mock_q_rep.coherence_score = 0.8
    mock_q_rep.hook_retention = 0.8
    mock_quality.score_all = AsyncMock(return_value=mock_q_rep)

    mock_narrative = MagicMock()
    mock_narrative.score = AsyncMock(return_value={"score": 0.8})

    scorer = PrototypeScorer(quality_scorer=mock_quality, narrative_scorer=mock_narrative)
    res = scorer.score_sync(2, "同期スコアリングテスト本文")

    assert isinstance(res, EpisodeScore)
    assert res.ep == 2
    assert res.total_score > 0.0
