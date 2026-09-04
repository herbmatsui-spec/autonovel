# tests/integration/test_planning_3gacha.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from src.backend.planning_service import PlanningService
from src.services.book_score_service import BookScoreCalculator


@dataclass
class Arc:
    start_ep: int
    end_ep: int
    title: str
    summary: str


@pytest.fixture
def mock_bible_generator():
    gen = MagicMock()
    gen.create_hegemony_plan = AsyncMock(return_value=(1, {"arcs": []}))
    return gen


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo._session_factory = MagicMock()
    return repo


@pytest.fixture
def mock_book_score_calculator():
    calc = MagicMock(spec=BookScoreCalculator)
    calc._get_weights = MagicMock(return_value={
        "structure": 35, "coherency": 10, "factual_grounding": 10,
        "visual_textual_synergy": 5, "reader_experience": 40,
    })
    return calc


@pytest.fixture
def mock_bible_generator():
    gen = MagicMock()
    gen.create_hegemony_plan = AsyncMock(return_value=(1, {"arcs": []}))
    return gen


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo._session_factory = MagicMock()
    return repo


@pytest.fixture
def mock_book_score_calculator():
    calc = MagicMock(spec=BookScoreCalculator)
    calc._get_weights = MagicMock(return_value={
        "structure": 35, "coherency": 10, "factual_grounding": 10,
        "visual_textual_synergy": 5, "reader_experience": 40,
    })
    return calc


@pytest.mark.asyncio
async def test_planning_service_3gacha_comparison(
    mock_bible_generator, mock_repo, mock_book_score_calculator
):
    """3案企画ガチャの比較評価・推奨案選出"""
    service = PlanningService(
        bible_generator=mock_bible_generator,
        repo=mock_repo,
        pm=MagicMock(),
        ctx_mgr=MagicMock(),
        reporter_factory=MagicMock(),
        book_score_calculator=mock_book_score_calculator,
    )

    # 3つの異なるアーク構成案
    proposal_a = [  # バランス良い3アーク
        Arc(start_ep=1, end_ep=3, title="導入", summary=""),
        Arc(start_ep=4, end_ep=7, title="展開", summary=""),
        Arc(start_ep=8, end_ep=10, title="クライマックス", summary=""),
    ]
    
    proposal_b = [  # アーク数多すぎ（5アーク）
        Arc(start_ep=1, end_ep=2, title="導入1", summary=""),
        Arc(start_ep=3, end_ep=4, title="導入2", summary=""),
        Arc(start_ep=5, end_ep=6, title="展開", summary=""),
        Arc(start_ep=7, end_ep=8, title="転換", summary=""),
        Arc(start_ep=9, end_ep=10, title="クライマックス", summary=""),
    ]
    
    proposal_c = [  # アーク数少なすぎ（1アーク）、クライマックス位置不適切
        Arc(start_ep=1, end_ep=10, title="全編通し", summary=""),
    ]

    proposals = [proposal_a, proposal_b, proposal_c]
    
    results = await service.predict_book_score_for_proposals(
        proposals, genre="literary", target_eps=10
    )

    # 3案分の結果が返る
    assert len(results) == 3
    
    # 全案に必要なキーが含まれる
    for r in results:
        assert "proposal_index" in r
        assert "proposal_name" in r
        assert "overall_score" in r
        assert "rank" in r
        assert "recommended" in r
    
    # ランク順でソート済み（降順）
    scores = [r["overall_score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    
    # 1位のみ recommended=True
    recommended_count = sum(1 for r in results if r["recommended"])
    assert recommended_count == 1
    assert results[0]["recommended"] is True
    assert results[0]["rank"] == 1
    
    # 結果の妥当性確認（スコアが降順でソートされていること）
    # 実際のスコアリングロジックに基づき、最高スコア案が推奨される
    assert results[0]["overall_score"] >= results[1]["overall_score"]
    assert results[1]["overall_score"] >= results[2]["overall_score"]


@pytest.mark.asyncio
async def test_planning_service_single_proposal(
    mock_bible_generator, mock_repo, mock_book_score_calculator
):
    """単一案の予測も正常動作"""
    service = PlanningService(
        bible_generator=mock_bible_generator,
        repo=mock_repo,
        pm=MagicMock(),
        ctx_mgr=MagicMock(),
        reporter_factory=MagicMock(),
        book_score_calculator=mock_book_score_calculator,
    )

    arcs = [
        Arc(start_ep=1, end_ep=3, title="導入", summary=""),
        Arc(start_ep=4, end_ep=7, title="展開", summary=""),
        Arc(start_ep=8, end_ep=10, title="クライマックス", summary=""),
    ]

    result = await service.predict_book_score_from_outline(arcs, genre="literary", target_eps=10)
    
    assert "overall_score" in result
    assert "structure_score" in result
    assert "reader_experience_score" in result
    assert isinstance(result["overall_score"], float)
    assert 0 <= result["overall_score"] <= 100


@pytest.mark.asyncio
async def test_planning_service_empty_arcs(
    mock_bible_generator, mock_repo, mock_book_score_calculator
):
    """空アークリストで低スコア返却"""
    service = PlanningService(
        bible_generator=mock_bible_generator,
        repo=mock_repo,
        pm=MagicMock(),
        ctx_mgr=MagicMock(),
        reporter_factory=MagicMock(),
        book_score_calculator=mock_book_score_calculator,
    )

    result = await service.predict_book_score_from_outline([], genre="literary", target_eps=10)
    
    # 構造スコアが低い（30点）ため、全体も低い
    assert result["structure_score"] == 30.0
    assert result["overall_score"] < 50.0


@pytest.mark.asyncio
async def test_planning_service_no_calculator(
    mock_bible_generator, mock_repo
):
    """BookScoreCalculator なしでもエラーにならない"""
    service = PlanningService(
        bible_generator=mock_bible_generator,
        repo=mock_repo,
        pm=MagicMock(),
        ctx_mgr=MagicMock(),
        reporter_factory=MagicMock(),
        book_score_calculator=None,
    )

    arcs = [Arc(start_ep=1, end_ep=10, title="単一アーク", summary="")]
    result = await service.predict_book_score_from_outline(arcs, genre="literary", target_eps=10)
    
    assert result["overall_score"] == 0.0
    assert result["structure_score"] == 0.0
    assert result["reader_experience_score"] == 0.0