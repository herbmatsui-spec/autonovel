"""
tests/api/test_affinity_override.py - Phase 5: API Integration and HITL Affinity Override Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import ASGITransport, AsyncClient
from src.backend.server import app
from src.backend.workflows.narrative_state import NarrativeState


@pytest.mark.asyncio
async def test_override_affinity_api_endpoint():
    """ステップ 64〜71: POST /api/narrative/{book_id}/{branch_id}/affinity/override のテスト"""
    dummy_hub = NarrativeState(book_id=1, branch_id=1)
    dummy_hub.affinity_map["メインヒロイン"] = {"affinity_score": 60.0, "current_mood": "neutral"}

    with patch("src.backend.routers.narrative.UnitOfWork") as mock_uow_cls, \
         patch("src.backend.routers.narrative.get_sse_manager") as mock_sse_mgr:
        
        mock_uow = AsyncMock()
        mock_uow.__aenter__.return_value = mock_uow
        mock_uow.misc.load_narrative = AsyncMock(return_value=dummy_hub.to_dict())
        mock_uow.misc.save_narrative = AsyncMock()
        mock_uow_cls.return_value = mock_uow

        mock_sse = MagicMock()
        mock_sse.broadcast = AsyncMock()
        mock_sse_mgr.return_value = mock_sse

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            payload = {
                "character_name": "メインヒロイン",
                "affinity_score": 95.0,
                "dependency_score": 80.0,
                "current_mood": "deep_love"
            }
            res = await client.post("/api/narrative/1/1/affinity/override", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert data["character_name"] == "メインヒロイン"
            assert data["affinity_data"]["affinity_score"] == 95.0
            assert data["affinity_data"]["current_mood"] == "deep_love"

            # DB保存とSSEブロードキャストの呼び出しを検証
            mock_uow.misc.save_narrative.assert_called_once()
            mock_sse.broadcast.assert_called_once()
            call_args = mock_sse.broadcast.call_args
            assert call_args[0][0] == "affinity_overridden"
            assert call_args[0][1]["character_name"] == "メインヒロイン"
