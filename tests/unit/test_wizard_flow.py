"""tests/unit/test_wizard_flow.py - かんたんモード→Studio昇格フローの単体テスト."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.backend.server import app
from src.domain.entities.easy_mode import PromotionRequest, PromotionResponse
from src.services.promotion_service import PromotionService, build_state_token


def test_build_state_token():
    token1 = build_state_token()
    token2 = build_state_token()
    assert len(token1) >= 16
    assert token1 != token2


@pytest.mark.asyncio
async def test_promotion_service_no_db_fallback():
    service = PromotionService(db=None)
    req = PromotionRequest(book_id="draft-12345")
    res = await service.promote_book(req)

    assert res.success is True
    assert res.redirect_url == "/studio/draft-12345"
    assert len(res.state_token) >= 16


@pytest.mark.asyncio
async def test_promotion_service_with_numeric_book_id():
    mock_db = MagicMock()
    mock_session = AsyncMock()
    mock_db.get_session.return_value.__aenter__.return_value = mock_session

    # Draft は None だが、Book テーブルの検索結果がモックされる
    mock_draft_repo = AsyncMock()
    mock_draft_repo.load_digest = AsyncMock(return_value=None)

    mock_book_row = (1, "Test Book", "advanced")
    mock_result = MagicMock()
    mock_result.fetchone.return_value = mock_book_row
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("src.backend.database.repositories.EasyModeDraftRepository", return_value=mock_draft_repo):
        service = PromotionService(db=mock_db)
        req = PromotionRequest(book_id="1")
        res = await service.promote_book(req)

    assert res.success is True
    assert res.redirect_url == "/studio/1"
    assert len(res.state_token) >= 16


def test_wizard_promote_endpoint(client, monkeypatch):
    from src.backend.config import settings
    monkeypatch.setattr(settings, "AUTH_DISABLED", True)

    # 認証バイパスまたは有効なAPIキーでリクエスト
    mock_response = PromotionResponse(
        success=True,
        redirect_url="/studio/100",
        state_token="valid_state_token_12345",
    )

    with patch.object(PromotionService, "promote_book", new_callable=AsyncMock) as mock_promote:
        mock_promote.return_value = mock_response
        resp = client.post(
            "/api/wizard/promote",
            json={"book_id": "100"},
            headers={"X-API-Key": "test-key", "Authorization": "Bearer dev-token"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["redirect_url"] == "/studio/100"
    assert data["state_token"] == "valid_state_token_12345"
