import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import Request
from src.backend.routers.billing_webhook import handle_stripe_webhook
from src.backend.database.models_billing import StripeWebhookEvent

@pytest.mark.asyncio
async def test_billing_webhook_idempotency():
    event_id = "evt_test_idempotent_123"

    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"id": "evt_test_idempotent_123", "type": "checkout.session.completed"}')
    mock_request.headers = {"stripe-signature": "sig_test"}

    # Mock database session
    mock_db = AsyncMock()
    mock_existing_event = MagicMock(spec=StripeWebhookEvent)
    mock_existing_event.status = "processed"
    mock_db.get = AsyncMock(return_value=mock_existing_event)
    mock_db.commit = AsyncMock()

    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {"id": event_id, "type": "checkout.session.completed"}

        # 既に処理済みイベントの場合は即時 200 OK が返る
        response = await handle_stripe_webhook(mock_request, db=mock_db)
        assert response.get("status") == "already_processed"
        assert response.get("event_id") == event_id
