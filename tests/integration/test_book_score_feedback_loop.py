# tests/integration/test_book_score_feedback_loop.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.backend.writing_service import WritingService
from src.services.book_score_service import BookScoreCalculator
from src.agents.orchestrator import AgentContext


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo._session_factory = MagicMock()
    return repo


@pytest.fixture
def mock_writer():
    writer = MagicMock()
    writer.generate_episodes = AsyncMock(return_value=3000)
    writer.generate_episodes_pipeline = AsyncMock(return_value=(3000, []))
    return writer


@pytest.fixture
def mock_book_score_calculator():
    calc = MagicMock(spec=BookScoreCalculator)
    calc._get_weights = MagicMock(return_value={
        "structure": 25, "coherency": 25, "factual_grounding": 20,
        "visual_textual_synergy": 15, "reader_experience": 15,
    })
    return calc


@pytest.mark.asyncio
async def test_writing_service_regeneration_loop_success(
    mock_repo, mock_writer, mock_book_score_calculator
):
    """BookScore 閾値未満 → 再生成 → 閾値達成で停止"""
    # 1回目: 低スコア、2回目: 高スコア、3回目: 最終確認
    call_count = 0
    
    async def mock_calculate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # 1回目: 閾値未満
            return MagicMock(
                overall_score=60.0,
                structure_score=50.0,
                coherency_score=65.0,
                factual_grounding_score=70.0,
                visual_textual_synergy_score=55.0,
                reader_experience_score=60.0,
            )
        else:
            # 2回目以降: 閾値達成
            return MagicMock(
                overall_score=80.0,
                structure_score=85.0,
                coherency_score=75.0,
                factual_grounding_score=80.0,
                visual_textual_synergy_score=85.0,
                reader_experience_score=75.0,
            )
    
    mock_book_score_calculator.calculate = mock_calculate

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

    # 執筆実行
    word_count = await service.generate_episodes(
        book_id=1, start_ep=1, end_ep=1,
        passion=0.8, target_word_count=3000,
        is_easy_mode=False, reporter=MagicMock(),
        auto_regenerate=True, max_retries=3,
    )
    
    assert word_count == 3000
    assert call_count >= 2  # 初回失敗→再生成→成功で最低2回呼ばれる
    assert mock_writer.generate_episodes.call_count == 2


@pytest.mark.asyncio
async def test_writing_service_regeneration_max_retries(
    mock_repo, mock_writer, mock_book_score_calculator
):
    """最大リトライ回数到達で停止"""
    # 常に低スコアを返す
    mock_book_score_calculator.calculate = AsyncMock(return_value=MagicMock(
        overall_score=50.0,
        structure_score=40.0,
        coherency_score=50.0,
        factual_grounding_score=60.0,
        visual_textual_synergy_score=45.0,
        reader_experience_score=50.0,
    ))

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

    reporter = MagicMock()
    word_count = await service.generate_episodes(
        book_id=1, start_ep=1, end_ep=1,
        passion=0.8, target_word_count=3000,
        is_easy_mode=False, reporter=reporter,
        auto_regenerate=True, max_retries=3,
    )
    
    # 初回 + 3回リトライ = 4回呼ばれる
    assert mock_writer.generate_episodes.call_count == 4
    # エラーログが出力されることを確認
    error_calls = [c for c in reporter.report.call_args_list if c[0][1] == "error"]
    assert len(error_calls) > 0


@pytest.mark.asyncio
async def test_writing_service_no_regeneration_when_disabled(
    mock_repo, mock_writer, mock_book_score_calculator
):
    """auto_regenerate=False の場合は再生成しない"""
    mock_book_score_calculator.calculate = AsyncMock(return_value=MagicMock(
        overall_score=50.0,  # 閾値未満
        structure_score=40.0,
        coherency_score=50.0,
        factual_grounding_score=60.0,
        visual_textual_synergy_score=45.0,
        reader_experience_score=50.0,
    ))

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

    word_count = await service.generate_episodes(
        book_id=1, start_ep=1, end_ep=1,
        passion=0.8, target_word_count=3000,
        is_easy_mode=False, reporter=MagicMock(),
        auto_regenerate=False,  # 無効
        max_retries=3,
    )
    
    # 再生成なしで1回のみ
    assert mock_writer.generate_episodes.call_count == 1


@pytest.mark.asyncio
async def test_writing_service_regeneration_actions_generated(
    mock_repo, mock_writer, mock_book_score_calculator
):
    """再生成アクションが正しく生成される"""
    mock_book_score_calculator.calculate = AsyncMock(return_value=MagicMock(
        overall_score=60.0,
        structure_score=50.0,   # 低
        coherency_score=55.0,   # 低
        factual_grounding_score=70.0,
        visual_textual_synergy_score=80.0,
        reader_experience_score=85.0,
    ))

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

    result = await service.calculate_book_score(book_id=1, chapter_number=1)
    
    assert result["regeneration_triggered"] is True
    assert "structure" in result["low_dimensions"]
    assert "coherency" in result["low_dimensions"]
    assert len(result["regeneration_actions"]) == 2
    
    # アクションの内容確認
    actions = {a["dimension"]: a for a in result["regeneration_actions"]}
    assert actions["structure"]["target_agent"] == "ContextBuilderAgent"
    assert actions["coherency"]["target_agent"] == "ContextBuilderAgent"
    assert actions["structure"]["params"]["enhance_arc_alignment"] is True
    assert actions["coherency"]["params"]["enhance_speech_profiles"] is True