# tests/unit/test_book_score_service.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.book_score_service import BookScoreCalculator, BookScoreRepository, BookScore
from src.infrastructure.database.models.book_score import BookScore as BookScoreModel
from src.agents.orchestrator import AgentContext


class MockBookScoreRepository:
    def __init__(self):
        self.saved_scores = []

    async def save(self, score: BookScoreModel) -> None:
        self.saved_scores.append(score)

    async def get_latest(self, book_id: int, chapter_number: int) -> BookScoreModel | None:
        for s in reversed(self.saved_scores):
            if s.book_id == book_id and s.chapter_number == chapter_number:
                return s
        return None


@pytest.fixture
def mock_repo():
    return MockBookScoreRepository()


@pytest.fixture
def calculator(mock_repo):
    with patch("src.services.book_score_service.open", create=True) as mock_open:
        import yaml
        config = yaml.dump({
            "default": {
                "structure": 25,
                "coherency": 25,
                "factual_grounding": 20,
                "visual_textual_synergy": 15,
                "reader_experience": 15,
            },
            "genre_overrides": {},
            "phase_overrides": {},
        })
        mock_open.return_value.__enter__.return_value.read.return_value = config
        calc = BookScoreCalculator(config_path="dummy.yaml", repository=mock_repo)
        return calc


@pytest.mark.asyncio
async def test_calculate_returns_bookscore(calculator):
    """calculate メソッドが BookScore を返すこと"""
    score = await calculator.calculate(book_id=1, chapter_number=1, genre="literary", phase="planning")
    assert isinstance(score, BookScore)
    assert 0 <= score.overall_score <= 100
    assert all(0 <= getattr(score, f"{dim}_score") <= 100 for dim in [
        "structure", "coherency", "factual_grounding", "visual_textual_synergy", "reader_experience"
    ])


@pytest.mark.asyncio
async def test_weights_applied(calculator):
    """重みが正しく適用されること"""
    # 全次元50点の場合、重み付け合計も50点
    calculator._score_structure = AsyncMock(return_value=50.0)
    calculator._score_coherency = AsyncMock(return_value=50.0)
    calculator._score_factual = AsyncMock(return_value=50.0)
    calculator._score_visual_textual = AsyncMock(return_value=50.0)
    calculator._score_reader_experience = AsyncMock(return_value=50.0)

    score = await calculator.calculate(book_id=1, chapter_number=1)
    assert score.overall_score == 50.0


@pytest.mark.asyncio
async def test_genre_override(calculator):
    """ジャンル別オーバーライドが機能すること"""
    # literary: structure=30, reader_experience=25
    calculator._score_structure = AsyncMock(return_value=100.0)
    calculator._score_reader_experience = AsyncMock(return_value=100.0)
    calculator._score_coherency = AsyncMock(return_value=0.0)
    calculator._score_factual = AsyncMock(return_value=0.0)
    calculator._score_visual_textual = AsyncMock(return_value=0.0)

    score = await calculator.calculate(book_id=1, chapter_number=1, genre="literary")
    # structure(30%) + reader_exp(25%) = 55点
    assert score.overall_score == 55.0


@pytest.mark.asyncio
async def test_save_score(calculator, mock_repo):
    """スコアが保存されること"""
    calculator._score_structure = AsyncMock(return_value=50.0)
    calculator._score_coherency = AsyncMock(return_value=50.0)
    calculator._score_factual = AsyncMock(return_value=50.0)
    calculator._score_visual_textual = AsyncMock(return_value=50.0)
    calculator._score_reader_experience = AsyncMock(return_value=50.0)

    score = await calculator.calculate(book_id=1, chapter_number=1)
    assert len(mock_repo.saved_scores) == 1
    saved = mock_repo.saved_scores[0]
    assert saved.book_id == 1
    assert saved.chapter_number == 1
    assert saved.overall_score == 50.0


@pytest.mark.asyncio
async def test_get_latest_score(calculator, mock_repo):
    """最新スコアが取得できること"""
    # 直接保存
    model = BookScoreModel(
        book_id=1, chapter_number=1, overall_score=75.0,
        structure_score=80.0, coherency_score=70.0,
        factual_grounding_score=70.0, visual_textual_synergy_score=80.0,
        reader_experience_score=80.0, evaluated_at=datetime.utcnow(), evaluator_version="1.0"
    )
    await mock_repo.save(model)

    latest = await calculator.get_latest_score(1, 1)
    assert latest is not None
    assert latest.overall_score == 75.0


@pytest.mark.asyncio
async def test_save_score_no_repo():
    """リポジトリなしでもエラーにならないこと"""
    with patch("src.services.book_score_service.open", create=True) as mock_open:
        import yaml
        config = yaml.dump({"default": {"structure": 25, "coherency": 25, "factual_grounding": 20, "visual_textual_synergy": 15, "reader_experience": 15}})
        mock_open.return_value.__enter__.return_value.read.return_value = config
        calc = BookScoreCalculator(config_path="dummy.yaml", repository=None)
        calc._score_structure = AsyncMock(return_value=50.0)
        calc._score_coherency = AsyncMock(return_value=50.0)
        calc._score_factual = AsyncMock(return_value=50.0)
        calc._score_visual_textual = AsyncMock(return_value=50.0)
        calc._score_reader_experience = AsyncMock(return_value=50.0)

        # エラーにならないこと
        score = await calc.calculate(book_id=1, chapter_number=1)
        assert score.overall_score == 50.0