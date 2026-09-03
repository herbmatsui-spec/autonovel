# tests/integration/test_orchestrated_api.py
"""オーケストレーション API 統合テスト。

注: 既存ルーターの `illustration_agent.run(request=...)` 呼び出しが新シグネチャ
`(ctx: AgentContext)` と互換性がないため、`server.py` の動的ルーター登録が
ハングする場合がある。本テストはオーケストレーションルーターのみを
ロードして検証する。
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestOrchestratedAPI:
    """オーケストレーション API テスト（ルーター単独ロード）。"""

    def _build_minimal_app(self):
        """オーケストレーションルーターのみを含む最小 FastAPI アプリ。"""
        app = FastAPI()
        from src.backend.routers.orchestrated import router as orchestrated_router

        app.include_router(orchestrated_router, prefix="/orchestrated", tags=["orchestrated"])
        return app

    @patch("src.backend.tasks.generation_tasks.generate_chapter_orchestrated_task")
    def test_generate_endpoint_returns_task_id(self, mock_task):
        """POST /orchestrated/generate が task_id を返すこと。"""
        # テストごとにユニークな task_id を使う (共有DB の UNIQUE 制約回避)
        import uuid
        unique_id = f"test-task-{uuid.uuid4().hex[:8]}"
        mock_result = MagicMock()
        mock_result.id = unique_id
        mock_task.return_value = mock_result

        app = self._build_minimal_app()
        client = TestClient(app)

        payload = {
            "book_id": 1,
            "branch_id": 1,
            "ep_num": 1,
            "title": "テスト作品",
            "synopsis": "テストあらすじ",
            "target_eps": 10,
            "genre": "fantasy",
        }
        response = client.post("/orchestrated/generate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        assert isinstance(data["message"], str)

    def test_generate_endpoint_validation(self):
        """必須フィールド未入力で 422 が返ること。"""
        app = self._build_minimal_app()
        client = TestClient(app)

        payload = {"book_id": 1}  # title 未入力
        response = client.post("/orchestrated/generate", json=payload)
        assert response.status_code == 422

    def test_status_endpoint_pending(self):
        """GET /orchestrated/status/{task_id} で存在しないタスクは pending。"""
        app = self._build_minimal_app()
        client = TestClient(app)

        response = client.get("/orchestrated/status/nonexistent_task_id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["task_id"] == "nonexistent_task_id"

    @patch("src.backend.routers.orchestrated.huey")
    def test_cancel_endpoint(self, mock_huey):
        """DELETE /orchestrated/task/{task_id} が 200 を返すこと。"""
        app = self._build_minimal_app()
        client = TestClient(app)

        import uuid
        unique_id = f"test-task-{uuid.uuid4().hex[:8]}"
        response = client.delete(f"/orchestrated/task/{unique_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"
        assert data["task_id"] == unique_id