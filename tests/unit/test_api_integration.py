"""tests/test_api_integration.py - APIエンドポイント統合テスト"""

import os

os.environ.setdefault("ALLOWED_API_KEYS", "test-api-key")

import pytest
from httpx import ASGITransport, AsyncClient

from src.backend.server import app

AUTH_HEADERS = {"X-API-Key": "test-api-key"}


@pytest.mark.asyncio
async def test_produce_novel_endpoint():
    """作品生成エンドポイントのテスト"""
    payload = {
        "title": "テスト作品",
        "genre": "fantasy",
        "synopsis": "テスト用あらすじ",
        "keywords": ["戦士", "魔法"],
        "target_episodes": 3,
        "target_word_count": 2000,
        "style_key": "default",
        "engine_key": "standard",
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/novel/produce", json=payload, headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["project_id"] == 1


@pytest.mark.asyncio
async def test_get_novel_status():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/novel/1/status", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "project_id" in data
        assert "status" in data
        assert "progress_percent" in data


@pytest.mark.asyncio
async def test_list_episodes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/novel/1/episodes", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "episodes" in data
        assert isinstance(data["episodes"], list)


@pytest.mark.asyncio
async def test_get_report():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/novel/1/report", headers=AUTH_HEADERS)
        assert response.status_code == 200
        data = response.json()
        assert "report" in data
        assert isinstance(data["report"], dict)
