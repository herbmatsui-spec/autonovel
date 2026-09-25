"""
本物の FastAPI Easy Mode API 整合性検証テスト (Step 7)
"""

import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.backend.server import app


@pytest.fixture
def test_client():
    """FastAPI TestClient フィクスチャ (エラー原因特定の詳細例外スロー有効)"""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


def test_easy_mode_invalid_input_returns_422(test_client):
    """制限範囲外（content_length_limit=0 など）送信時に 422 Unprocessable Entity が返ること"""
    response = test_client.post(
        "/easy_mode/generate",
        json={"content_length_limit": 0}  # ge=1 なのでバリデーション違反
    )
    assert response.status_code == 422


@patch("src.backend.tasks.generation_tasks.generate_chapter_orchestrated_task")
def test_easy_mode_generate_enqueues_task(mock_task, test_client):
    """有効なリクエスト送信時に非同期生成タスクがキューに投入され、タスクIDが返ること"""
    unique_task_id = f"test-task-{uuid.uuid4()}"
    mock_result = MagicMock()
    mock_result.id = unique_task_id
    mock_task.return_value = mock_result

    payload = {
        "character_params": {
            "name": "アレン",
            "personality": "冷静沈着",
            "ability": "空間魔法"
        },
        "current_chapter": "第1話：目覚め",
        "genre": "異世界ファンタジー",
        "content_length_limit": 2000,
        "target_episodes": 1
    }

    response = test_client.post("/easy_mode/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["task_id"] == unique_task_id
    assert "suggestions" in data
