# tests/unit/test_book_score_api.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi.testclient import TestClient

from src.backend.server import app
from src.infrastructure.database.models.book_score import BookScore as BookScoreModel


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_uow():
    """UnitOfWorkをモックし、内部のリポジトリもモックする"""
    # 複数のルーターでUnitOfWorkが使用されているため、両方をパッチする
    with patch("src.backend.routers.books.UnitOfWork") as mock_uow_books, \
         patch("src.backend.routers.novel.UnitOfWork") as mock_uow_novel:
        
        mock_uow_instance = AsyncMock()
        # コンテキストマネージャの挙動をシミュレート
        mock_uow_books.return_value.__aenter__.return_value = mock_uow_instance
        mock_uow_novel.return_value.__aenter__.return_value = mock_uow_instance
        
        # リポジトリのモック
        mock_uow_instance.books = AsyncMock()
        mock_uow_instance.book_scores = AsyncMock()
        mock_uow_instance.pdca_history = AsyncMock()
        
        yield mock_uow_instance


def test_get_chapter_book_score_success(client, mock_uow):
    """BookScore 取得エンドポイントが正常に動作すること"""
    # Mock setup
    mock_uow.books.get_book = AsyncMock(return_value=MagicMock(id=1))
    mock_uow.book_scores.get_latest = AsyncMock(return_value=BookScoreModel(
        book_id=1, chapter_number=1, overall_score=85.5,
        structure_score=90.0, coherency_score=85.0,
        factual_grounding_score=80.0, visual_textual_synergy_score=85.0,
        reader_experience_score=90.0, evaluated_at=datetime.utcnow(), evaluator_version="1.0"
    ))
    
    response = client.get("/api/novel/books/1/chapters/1/score")
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == 1
    assert data["chapter_number"] == 1
    assert data["overall_score"] == 85.5
    assert data["structure_score"] == 90.0


def test_get_chapter_book_score_not_found(client, mock_uow):
    """存在しないスコアは404を返すこと"""
    # router は calculator.get_latest_score (uow.book_scores.get_latest) を使用する
    mock_uow.book_scores.get_latest = AsyncMock(return_value=None)
    
    response = client.get("/api/novel/books/999/chapters/1/score")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_book_score_history_success(client, mock_uow):
    """BookScore履歴取得APIが正常に動作すること (Step 31, 34)"""
    # Mock setup
    mock_uow.books.get_book = AsyncMock(return_value=MagicMock(id=1, genre="Fantasy"))
    mock_uow.book_scores.get_history_for_book = AsyncMock(return_value=[
        BookScoreModel(
            book_id=1, chapter_number=1, overall_score=80.0,
            structure_score=80.0, coherency_score=80.0,
            factual_grounding_score=80.0, visual_textual_synergy_score=80.0,
            reader_experience_score=80.0, evaluated_at=datetime.utcnow(), evaluator_version="1.0"
        ),
        BookScoreModel(
            book_id=1, chapter_number=1, overall_score=85.0,
            structure_score=85.0, coherency_score=85.0,
            factual_grounding_score=85.0, visual_textual_synergy_score=85.0,
            reader_experience_score=85.0, evaluated_at=datetime.utcnow(), evaluator_version="1.1"
        ),
    ])
    mock_uow.book_scores.get_genre_benchmarks = AsyncMock(return_value={
        "Fantasy": {
            "structure": 75.0, "coherency": 70.0, "factual": 60.0, "visual": 80.0, "reader": 75.0, "overall": 74.0
        }
    })
    
    response = client.get("/api/books/1/book-scores/history")
    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert len(data["history"]) == 2
    assert "benchmarks" in data
    # benchmarks は指定ジャンルのデータ（dict）が直接返ってくる
    assert data["benchmarks"]["overall"] == 74.0


@pytest.mark.asyncio
async def test_get_pdca_cycles_success(client, mock_uow):
    """PDCAサイクル履歴取得APIが正常に動作すること (Step 32)"""
    # Mock setup
    mock_uow.pdca_history.get_by_chapter = AsyncMock(return_value=[
        MagicMock(
            book_id=1, chapter_number=1, cycle_number=1,
            initial_score=70.0, final_score=80.0, score_delta=10.0,
            improved_percentage=14.2, lowest_dimension="structure",
            directives=[{
                "dimension": "structure",
                "severity": "medium",
                "target_location": "chapter 1",
                "current_issue": "Flow is choppy",
                "mandatory_instruction": "Improve flow",
                "rationale": "Better readability",
                "specialist_name": "Structure Specialist"
            }],
            history=[{
                "cycle": 1,
                "draft_chars": 2000,
                "score": 70.0,
                "scores_by_specialist": {"structure": 60.0, "coherency": 80.0},
                "calibrated_scores": {"structure": 65.0, "coherency": 75.0},
                "lowest_dimension": "structure",
                "directives_count": 1,
                "delta": 0.0
            }],
            converged=True, created_at=datetime.utcnow()
        )
    ])
    
    response = client.get("/api/books/1/pdca/cycles/1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["chapter_number"] == 1

