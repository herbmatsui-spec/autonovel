"""
Stripe Webhook べき等性とタイムアウト再試行テスト
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from src.backend.database.models import Base
from src.backend.database.models_billing import StripeWebhookEvent
from src.backend.routers.billing_webhook import handle_stripe_webhook


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _make_dummy_request(event_dict: dict) -> Request:
    import json
    body_bytes = json.dumps(event_dict).encode("utf-8")

    async def receive():
        return {"type": "http.request", "body": body_bytes}

    return Request(
        scope={"type": "http", "method": "POST", "headers": []},
        receive=receive,
    )


@pytest.mark.asyncio
async def test_webhook_idempotency_flow():
    async with TestingSessionLocal() as db:
        event_id = "evt_test_123"
        req = _make_dummy_request({
            "id": event_id,
            "type": "unhandled_dummy_event",
            "data": {"object": {}},
        })

        # 1. 初回受信 -> 成功
        res1 = await handle_stripe_webhook(request=req, stripe_signature="", db=db)
        assert res1["status"] == "success"
        assert res1["event_id"] == event_id

        # DB内のレコード検証
        evt = await db.get(StripeWebhookEvent, event_id)
        assert evt is not None
        assert evt.status == "processed"

        # 2. 2回目受信（重複） -> already_processed で安全にスキップ
        res2 = await handle_stripe_webhook(request=req, stripe_signature="", db=db)
        assert res2["status"] == "already_processed"
        assert res2["event_id"] == event_id


@pytest.mark.asyncio
async def test_webhook_stuck_processing_retried():
    async with TestingSessionLocal() as db:
        event_id = "evt_stuck_456"
        # 15分前から stuck している processing イベントを登録
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        stuck_evt = StripeWebhookEvent(
            event_id=event_id,
            event_type="unhandled_dummy_event",
            status="processing",
            created_at=stale_time,
        )
        db.add(stuck_evt)
        await db.commit()

        req = _make_dummy_request({
            "id": event_id,
            "type": "unhandled_dummy_event",
            "data": {"object": {}},
        })

        # タイムアウト検知により再処理が実行される
        res = await handle_stripe_webhook(request=req, stripe_signature="", db=db)
        assert res["status"] == "success"

        await db.refresh(stuck_evt)
        assert stuck_evt.status == "processed"
