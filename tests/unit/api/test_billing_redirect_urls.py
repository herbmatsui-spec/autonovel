"""決済リダイレクトURLが設定値のみから構成されることの回帰テスト。"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from src.backend.routers import billing


@pytest.mark.asyncio
async def test_checkout_urls_ignore_client_supplied_values():
    captured: dict = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return "https://stripe.example/checkout"

    with patch.object(billing.StripeClient, "create_checkout_session", staticmethod(fake_create)), \
         patch.object(billing.settings, "FRONTEND_URL", "https://novel.example"):
        result = await billing.create_checkout_session(
            request={"price_id": "price_123", "success_url": "https://evil.example", "cancel_url": "https://evil.example"},
            current_user=MagicMock(id=1, email="test@example.com"),
            db=MagicMock(),
        )
    assert result["checkout_url"] == "https://stripe.example/checkout"
    assert "https://evil.example" not in str(captured)
    assert captured["success_url"] == "https://novel.example/billing/success"
    assert captured["cancel_url"] == "https://novel.example/billing/cancel"


@pytest.mark.asyncio
async def test_portal_url_ignores_client_supplied_values():
    captured: dict = {}

    def fake_portal(**kwargs):
        captured.update(kwargs)
        return "https://stripe.example/portal"

    with patch.object(billing.StripeClient, "create_customer_portal_session", staticmethod(fake_portal)), \
         patch.object(billing.settings, "FRONTEND_URL", "https://novel.example"):
        result = await billing.create_portal_session(
            request={"return_url": "https://evil.example"},
            current_user=MagicMock(stripe_customer_id="cus_1"),
        )
    assert result["portal_url"] == "https://stripe.example/portal"
    assert captured["return_url"] == "https://novel.example/billing"
