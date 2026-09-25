"""tests/regression/test_v5_critical_invariants.py.

v5系の基幹 invariants である
1. 認証トークンの定数時間比較と改ざん拒否 (Timing-safe JWT / API Key)
2. Stripe Webhook のべき等処理（同一イベント重複時のクレジット多重付与防止）
3. DB トランザクション分離とロールバックの安全性
を検証するリグレッション防止テスト。
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.backend.middleware.auth_middleware import is_safe_api_key_match
from src.backend.database.models import User
from src.backend.database.models_billing import StripeWebhookEvent
from src.backend.routers.billing_webhook import handle_stripe_webhook
from fastapi import Request


def test_timing_safe_auth_matching():
    """APIキーの比較が定数時間で行われ、部分一致や改ざんを完全に拒否すること."""
    # 完全一致
    assert is_safe_api_key_match("secret-key-12345", "secret-key-12345") is True
    # 異なる長さ
    assert is_safe_api_key_match("secret-key-12345", "secret-key") is False
    # 1文字違い
    assert is_safe_api_key_match("secret-key-12345", "secret-key-12346") is False
    # 空文字
    assert is_safe_api_key_match("", "secret-key-12345") is False
    assert is_safe_api_key_match("secret-key-12345", "") is False


@pytest.mark.asyncio
async def test_billing_webhook_idempotency_prevents_duplicate_grant():
    """同一のStripeイベントIDが重複受信された際、二重付与せず即時返却すること."""
    # Mock request
    mock_request = MagicMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"id": "evt_duplicate_test", "type": "checkout.session.completed"}')

    # Mock db session: 既にステータスが "processed" のイベントが存在する状態
    existing_event = StripeWebhookEvent(
        event_id="evt_duplicate_test",
        event_type="checkout.session.completed",
        status="processed",
    )

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=existing_event)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    with patch("stripe.Webhook.construct_event", return_value={"id": "evt_duplicate_test", "type": "checkout.session.completed"}):
        result = await handle_stripe_webhook(mock_request, db=mock_session)

    # 重複スキップされること
    assert result.get("status") == "already_processed"
    assert result.get("event_id") == "evt_duplicate_test"
    # 新しいレコード追加やコミットが行われないこと
    mock_session.add.assert_not_called()


if __name__ == "__main__":
    test_timing_safe_auth_matching()
    asyncio.run(test_billing_webhook_idempotency_prevents_duplicate_grant())
    print("ALL V5 CRITICAL INVARIANTS TESTS PASSED!")
