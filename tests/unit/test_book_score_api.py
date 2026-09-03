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
def mock_session():
    session = AsyncMock()
    # BookScoreRepository.get_latest をモック
    async def mock_get_latest(book_id, chapter_number):
        if book_id == 1 and chapter_number == 1:
            return BookScoreModel(
                book_id=1, chapter_number=1, overall_score=85.5,
                structure_score=90.0, coherency_score=85.0,
                factual_grounding_score=80.0, visual_textual_synergy_score=85.0,
                reader_experience_score=90.0, evaluated_at=datetime.utcnow(), evaluator_version="1.0"
            )
        return None

    with patch("src.backend.routers.novel.BookScoreRepository") as mock_repo_class:
        mock_repo = mock_repo_class.return_value
        mock_repo.get_latest = mock_get_latest
        yield


def test_get_chapter_book_score_success(client, mock_session):
    """BookScore 取得エンドポイントが正常に動作すること"""
    response = client.get("/api/novel/books/1/chapters/1/score")
    assert response.status_code == 200
    data = response.json()
    assert data["book_id"] == 1
    assert data["chapter_number"] == 1
    assert data["overall_score"] == 85.5
    assert data["structure_score"] == 90.0


def test_get_chapter_book_score_not_found(client, mock_session):
    """存在しないスコアは404を返すこと"""
    response = client.get("/api/novel/books/999/chapters/1/score")
    assert response.status_code == 404