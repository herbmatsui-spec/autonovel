# tests/unit/test_planning_writing_integration.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.backend.planning_service import PlanningService
from src.backend.writing_service import WritingService
from src.services.book_score_service import BookScoreCalculator
from src.agents.orchestrator import AgentContext


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
    calc.calculate = AsyncMock(return_value=MagicMock(
        overall_score=80.0,
        structure_score=85.0,
        coherency_score=75.0,
        factual_grounding_score=80.0,
        visual_textual_synergy_score=85.0,
        reader_experience_score=75.0,
    ))
    calc._get_weights = MagicMock(return_value={
        "structure": 25, "coherency": 25, "factual_grounding": 20,
        "visual_textual_synergy": 15, "reader_experience": 15,
    })
    return calc


@pytest.fixture
def mock_writer():
    writer = MagicMock()
    writer.generate_episodes = AsyncMock(return_value=3000)
    writer.generate_episodes_pipeline = AsyncMock(return_value=(3000, []))
    return writer


@pytest.mark.asyncio
async def test_planning_service_with_book_score(
    mock_bible_generator, mock_repo, mock_book_score_calculator
):
    """PlanningService が BookScoreCalculator を使って予測できること"""
    service = PlanningService(
        bible_generator=mock_bible_generator,
        repo=mock_repo,
        pm=MagicMock(),
        ctx_mgr=MagicMock(),
        reporter_factory=MagicMock(),
        book_score_calculator=mock_book_score_calculator,
    )

    # Arc オブジェクトを作成
    from src.models.plot import Arc
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


@pytest.mark.asyncio
async def test_writing_service_with_book_score(
    mock_repo, mock_writer, mock_book_score_calculator
):
    """WritingService が BookScoreCalculator を使って評価できること"""
    service = WritingService(
        writer=mock_writer,
        repo=mock_repo,
        pm=MagicMock(),
        style_rag=MagicMock(),
        ctx_mgr=MagicMock(),
        reporter_factory=MagicMock(),
        book_score_calculator=mock_book_score_calculator,
        score_threshold=70.0,
    )

    # 執筆
    word_count = await service.generate_episodes(
        book_id=1, start_ep=1, end_ep=1,
        passion=0.8, target_word_count=3000,
        is_easy_mode=False, reporter=MagicMock(),
    )
    assert word_count == 3000

    # BookScore 計算
    result = await service.calculate_book_score(book_id=1, chapter_number=1, genre="entertainment")

    assert result is not None
    assert result["overall_score"] == 80.0
    assert result["regeneration_triggered"] is False


@pytest.mark.asyncio
async def test_writing_service_regeneration_trigger(
    mock_repo, mock_writer
):
    """閾値未満で再生成トリガーが発火すること"""
    calc = MagicMock(spec=BookScoreCalculator)
    calc.calculate = AsyncMock(return_value=MagicMock(
        overall_score=60.0,
        structure_score=50.0,
        coherency_score=65.0,
        factual_grounding_score=70.0,
        visual_textual_synergy_score=55.0,
        reader_experience_score=60.0,
    ))
    calc._get_weights = MagicMock(return_value={
        "structure": 25, "coherency": 25, "factual_grounding": 20,
        "visual_textual_synergy": 15, "reader_experience": 15,
    })

    service = WritingService(
        writer=mock_writer,
        repo=mock_repo,
        pm=MagicMock(),
        style_rag=MagicMock(),
        ctx_mgr=MagicMock(),
        reporter_factory=MagicMock(),
        book_score_calculator=calc,
        score_threshold=70.0,
    )

    result = await service.calculate_book_score(book_id=1, chapter_number=1)

    assert result["regeneration_triggered"] is True
    assert "structure" in result["low_dimensions"]
    assert "visual_textual_synergy" in result["low_dimensions"]
    assert "reader_experience" in result["low_dimensions"]