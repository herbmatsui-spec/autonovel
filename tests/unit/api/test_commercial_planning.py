"""/commercial/planning の契約テスト（所有者検証・404・入力検証・Task 発行）。"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.backend.auth import get_current_user
from src.backend.server import app


@pytest.fixture
def owner(monkeypatch):
    user = SimpleNamespace(id=1, role="user")
    app.dependency_overrides[get_current_user] = lambda: user
    mock_verify = AsyncMock(return_value=SimpleNamespace(id=1, user_id=1))
    monkeypatch.setattr(
        "src.backend.routers.commercial_planning.verify_book_ownership",
        mock_verify,
    )
    yield user, mock_verify
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_beat_sheet_404_when_not_generated(owner):
    user, _ = owner
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/commercial/planning/99999")
    assert resp.status_code == 404
    assert "未生成" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_ownership_is_verified(owner):
    user, mock_verify = owner
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/commercial/planning/1")
    mock_verify.assert_awaited()


@pytest.mark.asyncio
async def test_generate_rejects_out_of_range_episodes(owner):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/commercial/planning/generate",
            json={"title": "T", "synopsis": "S", "target_episodes": 41},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_generate_returns_task_id(owner):
    with patch("src.backend.tasks.execute_service_workflow") as mock_exec, patch(
        "src.backend.task_helpers.create_task", new=AsyncMock()
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/commercial/planning/generate",
                json={"title": "T", "synopsis": "S", "book_id": 1},
            )
    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert data["task_id"].startswith("commercial_beats_")
    mock_exec.assert_called_once()
