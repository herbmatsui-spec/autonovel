"""
課金＆クレジット統合テスト

Stripeモックを用いた決済完了からクレジット反映、消費・枯渇ブロックのE2Eテスト
"""
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from src.backend.server import app
from src.backend.database import get_db
from src.backend.database.models import Base, User
from src.backend.database.models_billing import (
    CreditTransaction,
    Subscription,
)
from src.services.billing.credit_service import CreditService
from src.config.billing_plans import PLAN_CONFIG, TASK_CREDIT_COSTS
from src.backend.auth import get_current_user


# テスト用のインメモリSQLiteデータベース
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    """テスト用のデータベースセッションを提供"""
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """データベーステーブルの初期化とクリーンアップ"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db():
    """データベースセッションフィクスチャ"""
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db: AsyncSession):
    """テスト用ユーザーを作成"""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        display_name="Test User",
        plan_tier="free",
        status="active",
        credits=50,  # フリープランのデフォルトクレジット
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 認証依存性をオーバーライド
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def client():
    """AsyncClientフィクスチャ"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_credit_flow_success(client: AsyncClient, db: AsyncSession, test_user: User):
    """正常なクレジットフローをテスト: 決済 → クレジット付与 → 消費"""

    # 1. 初期状態の確認
    assert test_user.credits == 50

    # 2. クレジットサービスを使用してクレジットを付与（Stripe Webhookのシミュレーション）
    credit_service = CreditService(db)
    new_balance = await credit_service.grant_credits(
        user_id=test_user.id,
        amount=300,  # スタータープラン相当
        transaction_type="monthly_grant",
        description="テスト用クレジット付与",
        task_id=None,
    )

    # クレジットが正しく付与されたことを確認
    assert new_balance == 350  # 50 (初期) + 300 (付与)

    # データベースから直接確認
    result = await db.execute(
        select(CreditTransaction.balance_after)
        .where(CreditTransaction.user_id == test_user.id)
        .order_by(CreditTransaction.created_at.desc(), CreditTransaction.id.desc())
        .limit(1)
    )
    latest_balance = result.scalar_one()
    assert latest_balance == 350

    # 3. クレジットを消費（生成タスクのシミュレーション）
    cost = TASK_CREDIT_COSTS["writing_standard"]
    await credit_service.deduct_credits(
        user_id=test_user.id,
        amount=cost,
        transaction_type="consumption",
        description="テスト用クレジット消費",
        task_id="test-task-123",
    )

    # 消費後の残高を確認
    result = await db.execute(
        select(CreditTransaction.balance_after)
        .where(CreditTransaction.user_id == test_user.id)
        .order_by(CreditTransaction.created_at.desc(), CreditTransaction.id.desc())
        .limit(1)
    )
    latest_balance = result.scalar_one()
    assert latest_balance == 340  # 350 - 10


@pytest.mark.asyncio
async def test_insufficient_credits_blocking(client: AsyncClient, db: AsyncSession, test_user: User):
    """クレジット不足時のブロックをテスト"""

    credit_service = CreditService(db)

    # 現在のクレジットを確認（フリープランの50クレジット）
    balance = await credit_service.get_balance(test_user.id)
    assert balance == 50

    high_cost_task = TASK_CREDIT_COSTS["writing_climax_pro"]  # 25

    # クレジット追加
    await credit_service.grant_credits(
        user_id=test_user.id,
        amount=30,  # 50 + 30 = 80クレジット
        transaction_type="pack_purchase",
        description="テスト用クレジット購入",
        task_id=None,
    )

    balance = await credit_service.get_balance(test_user.id)
    assert balance == 80

    # 25クレジットのタスクを実行
    await credit_service.deduct_credits(
        user_id=test_user.id,
        amount=high_cost_task,
        transaction_type="consumption",
        description="高コストタスクのテスト",
        task_id="test-task-456",
    )

    balance = await credit_service.get_balance(test_user.id)
    assert balance == 55  # 80 - 25

    # さらに高コストのタスク（例: 60クレジット必要）は失敗するべき
    with pytest.raises(Exception):
        await credit_service.deduct_credits(
            user_id=test_user.id,
            amount=60,  # 現在55クレジットしかないので不足
            transaction_type="consumption",
            description="残高不足のテスト",
            task_id="test-task-789",
        )

    # 残高が変わっていないことを確認
    balance = await credit_service.get_balance(test_user.id)
    assert balance == 55


@pytest.mark.asyncio
async def test_stripe_webhook_handling(client: AsyncClient, db: AsyncSession, test_user: User):
    """Stripe Webhookの処理をテスト"""

    # ユーザーにStripe Customer IDを設定
    test_user.stripe_customer_id = "cus_test_123"
    await db.commit()

    # Webhookイベントをシミュレート
    mock_event = {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_123",
                "customer": "cus_test_123",
                "subscription": "sub_test_123",
                "metadata": {
                    "user_id": str(test_user.id),
                },
            }
        },
    }

    # Stripeのモック
    with patch("stripe.Webhook.construct_event") as mock_construct_event:
        mock_construct_event.return_value = mock_event

        with patch("stripe.Subscription.retrieve") as mock_retrieve:
            mock_subscription = MagicMock()
            mock_subscription.id = "sub_test_123"
            mock_subscription.customer = "cus_test_123"
            mock_subscription.status = "active"
            mock_price = MagicMock()
            mock_price.id = "price_starter"
            mock_item = MagicMock()
            mock_item.price = mock_price
            mock_subscription.items.data = [mock_item]
            mock_subscription.plan.nickname = "Starter Plan"
            mock_subscription.current_period_end = 1234567890

            mock_retrieve.return_value = mock_subscription

            response = await client.post(
                "/api/billing/webhook",
                json=mock_event,
                headers={"Stripe-Signature": "test_signature"},
            )

            assert response.status_code == 200
            assert response.json()["status"] == "success"

    # クレジットが付与されたことを確認
    credit_service = CreditService(db)
    balance = await credit_service.get_balance(test_user.id)
    assert balance == 350

    # サブスクリプションレコードが作成されたことを確認
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == test_user.id)
    )
    subscription = result.scalar_one_or_none()
    assert subscription is not None
    assert subscription.stripe_subscription_id == "sub_test_123"
    assert subscription.plan_tier == "price_starter"
    assert subscription.status == "active"


@pytest.mark.asyncio
async def test_api_endpoints(client: AsyncClient, db: AsyncSession, test_user: User):
    """課金関連APIエンドポイントをテスト"""

    # 1. プラン一覧取得
    response = await client.get("/api/billing/plans")
    assert response.status_code == 200
    data = response.json()
    assert "plans" in data
    plans = data["plans"]
    assert "free" in plans
    assert "starter" in plans
    assert "pro" in plans
    assert "enterprise" in plans

    # フリープランの情報を確認
    free_plan = plans["free"]
    assert free_plan["price_jpy"] == 0
    assert free_plan["monthly_credits"] == 50

    # 2. 残高取得
    response = await client.get("/api/billing/balance")
    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == 50
    assert data["plan_tier"] == "free"
    assert data["user_id"] == test_user.id

    # 3. クレジットを追加して残高を変更
    credit_service = CreditService(db)
    await credit_service.grant_credits(
        user_id=test_user.id,
        amount=100,
        transaction_type="pack_purchase",
        description="APIテスト用クレジット追加",
        task_id=None,
    )

    response = await client.get("/api/billing/balance")
    assert response.status_code == 200
    data = response.json()
    assert data["balance"] == 150

    # 4. 取引履歴取得
    response = await client.get("/api/billing/transactions")
    assert response.status_code == 200
    data = response.json()
    assert "transactions" in data
    transactions = data["transactions"]
    assert len(transactions) >= 1
    latest_tx = transactions[0]
    assert latest_tx["amount"] == 100
    assert latest_tx["transaction_type"] == "pack_purchase"