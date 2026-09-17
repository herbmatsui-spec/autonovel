import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request
from src.backend.routers.billing_webhook import handle_stripe_webhook

@pytest.mark.asyncio
async def test_stripe_webhook_grants_credits():
    # Mock request
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"id": "evt_test_123", "type": "checkout.session.completed", "data": {"object": {"id": "cs_test_123", "customer": "cus_test_123", "subscription": "sub_test_123"}}}')
    mock_request.headers = {"stripe-signature": "sig_test"}

    # Mock database session
    mock_session = AsyncMock()
    mock_user = MagicMock(id=1, credits=10, stripe_customer_id="cus_test_123", plan_tier="free")
    # Mock the query to get user by stripe_customer_id
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none = AsyncMock(return_value=mock_user)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.merge = AsyncMock(return_value=mock_user)

    # Mock Stripe.Webhook.construct_event to return our event
    with patch("stripe.Webhook.construct_event") as mock_construct:
        mock_construct.return_value = {"id": "evt_test_123", "type": "checkout.session.completed", "data": {"object": {"id": "cs_test_123", "customer": "cus_test_123", "subscription": "sub_test_123"}}}

        # Mock the Stripe Subscription retrieve
        with patch("stripe.Subscription.retrieve") as mock_sub_retrieve:
            mock_sub_retrieve.return_value = MagicMock(
                items=MagicMock(data=[MagicMock(price=MagicMock(id="price_test_123"))]),
                customer="cus_test_123"
            )

            # Mock the get_credits_for_price_id function to return 100 credits
            with patch("src.backend.routers.billing_webhook.get_credits_for_price_id", return_value=100):
                # Mock the get_tier_for_price_id function
                with patch("src.backend.routers.billing_webhook.get_tier_for_price_id", return_value="pro"):

                    # Call the handler
                    await handle_stripe_webhook(mock_request, db=mock_session)

                    # Assert that the user's credits were increased by 100
                    assert mock_user.credits == 110
                    assert mock_user.plan_tier == "pro"
                    # Assert that a StripeWebhookEvent record was added
                    assert mock_session.add.call_count >= 1
                    # Assert that commit was called
                    assert mock_session.commit.called
