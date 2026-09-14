import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch, MagicMock

from src.backend.server import app
from src.backend.database import get_db
from src.backend.database.models import Base, User
from src.backend.database.models_billing import StripeWebhookEvent, CreditTransaction
from src.core.container import AppContainer


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    original_db = AppContainer.db
    AppContainer.db = TestingSessionLocal
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    AppContainer.db = original_db
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_webhook_idempotency_prevents_duplicate_credit_grant():
    """同じStripeイベントIDが重複送信された場合、2回目はスキップされクレジット二重付与が防がれることを検証"""
    async with TestingSessionLocal() as session:
        user = User(
            email="subscriber@example.com",
            hashed_password="pw",
            display_name="Subscriber",
            stripe_customer_id="cus_test123",
            credits=50,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    fake_subscription = MagicMock()
    fake_subscription.id = "sub_test123"
    fake_subscription.customer = "cus_test123"
    fake_item = MagicMock()
    fake_item.price.id = "price_starter"
    fake_subscription.items.data = [fake_item]
    fake_subscription.plan.nickname = "Starter Plan"
    fake_subscription.status = "active"
    fake_subscription.current_period_end = 1770000000

    payload = {
        "id": "evt_unique_12345",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_abc",
                "customer": "cus_test123",
                "subscription": "sub_test123",
                "metadata": {"user_id": str(user.id)},
            }
        }
    }

    transport = ASGITransport(app=app)
    with patch("stripe.Subscription.retrieve", return_value=fake_subscription):
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1回目: 処理成功、starterプラン付与 (300クレジット追加 -> 350)
            res1 = await ac.post("/api/billing/webhook", json=payload)
            assert res1.status_code == 200
            assert res1.json()["status"] == "success"

            # 2回目: 同一イベントIDでリトライ受信 -> already_processed でスキップ
            res2 = await ac.post("/api/billing/webhook", json=payload)
            assert res2.status_code == 200
            assert res2.json()["status"] == "already_processed"

    async with TestingSessionLocal() as session:
        reloaded_user = await session.get(User, user.id)
        # クレジットは1回分（300）のみ付与されて 350 になっていること（650ではない）
        assert reloaded_user is not None
        assert reloaded_user.credits == 350
