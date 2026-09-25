"""課金・認証保護のE2Eテスト（Step 12）。

未認証アクセスの401遮断、認証済みアクセスの許可、クレジット消費のライフサイクルを全結合検証。
システム全体のリグレッション防止のためのベースラインテストとして機能する。
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.backend.server import app
from src.backend.config import settings
from src.backend.database import get_async_db
from src.backend.database.models import Base, User
from src.services.billing.credit_service import CreditService
from src.config.billing_plans import PLAN_CONFIG, get_credits_for_price_id
from src.backend.security.jwt import create_access_token


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_async_db():
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def setup_db(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_DISABLED", False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_async_db] = override_get_async_db
    yield
    app.dependency_overrides.pop(get_async_db, None)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def create_test_user(session: AsyncSession, email: str = "test@example.com", credits: int = 100) -> User:
    """テスト用ユーザーを作成する。"""
    user = User(
        email=email,
        hashed_password="test_hash",
        display_name="Test User",
        credits=credits,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


def create_auth_token(user_id: int) -> str:
    """テスト用の有効なJWTアクセストークンを生成する。"""
    return create_access_token(user_id=user_id, role="user")


def get_auth_headers(user: User) -> dict[str, str]:
    """認証ヘッダーを生成する。"""
    token = create_auth_token(user.id)
    return {"Authorization": f"Bearer {token}"}


class TestAuthProtection:
    """認証保護のテスト。"""

    @pytest.mark.asyncio
    async def test_unauthenticated_access_returns_401(self):
        """未認証アクセスは 401 エラーになること。"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 認証が必要なエンドポイントへのアクセス
            res = await ac.get("/api/cost/summary")
            assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_authenticated_access_allowed(self):
        """認証済みアクセスは許可されること。"""
        async with TestingSessionLocal() as session:
            user = await create_test_user(session)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 認証ヘッダー付きでアクセス
            headers = get_auth_headers(user)
            # コストサマリーAPI（認証が必要）
            res = await ac.get("/api/cost/summary", headers=headers)
            # 401 以外なら認証通過（実際のレスポンスはデータがあるかどうかで変わる）
            assert res.status_code != 401


class TestCreditLifecycle:
    """クレジット消費ライフサイクルのテスト。"""

    @pytest.mark.asyncio
    async def test_credit_grant_and_deduct_cycle(self):
        """クレジット付与→消費→残高確認のサイクル。"""
        async with TestingSessionLocal() as session:
            user = await create_test_user(session, credits=50)
            
            # クレジットサービスで残高確認
            credit_service = CreditService(session)
            initial_balance = await credit_service.get_balance(user.id)
            assert initial_balance == 50
            
            # クレジット付与
            new_balance = await credit_service.grant_credits(
                user_id=user.id,
                amount=100,
                transaction_type="monthly_grant",
                description="Test grant",
            )
            assert new_balance == 150
            
            # クレジット消費
            result = await credit_service.deduct_credits(
                user_id=user.id,
                amount=30,
                transaction_type="consumption",
                description="Test deduction",
            )
            assert result is True
            
            # 残高確認
            final_balance = await credit_service.get_balance(user.id)
            assert final_balance == 120

    @pytest.mark.asyncio
    async def test_insufficient_credits_prevents_deduction(self):
        """残高不足時は消費が防止されること。"""
        async with TestingSessionLocal() as session:
            user = await create_test_user(session, credits=10)
            credit_service = CreditService(session)
            
            # 所持クレジット以上の消費を試みる
            from src.services.billing.credit_service import InsufficientCreditsError
            
            with pytest.raises(InsufficientCreditsError):
                await credit_service.deduct_credits(
                    user_id=user.id,
                    amount=20,
                    transaction_type="consumption",
                    description="Should fail",
                )
            
            # 残高は変わらない
            balance = await credit_service.get_balance(user.id)
            assert balance == 10


class TestBillingIntegration:
    """課金システム統合テスト。"""

    @pytest.mark.asyncio
    async def test_monthly_credit_grant_amounts(self):
        """月次クレジット付与額がプラン設定と一致すること。"""
        from src.config.billing_plans import STRIPE_PRICE_TO_PLAN
        
        # 各プランの月次クレジットが正しく設定されているか確認
        for price_id, config in STRIPE_PRICE_TO_PLAN.items():
            credits = get_credits_for_price_id(price_id)
            assert credits == config["monthly_credits"], f"Price {price_id} credits mismatch"


class TestPerformanceRegression:
    """パフォーマンスリグレッションテスト。"""

    @pytest.mark.asyncio
    async def test_api_response_time_threshold(self):
        """API応答時間が閾値を超えないこと（簡易チェック）。"""
        import time
        
        async with TestingSessionLocal() as session:
            user = await create_test_user(session)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            headers = get_auth_headers(user)
            
            start = time.time()
            res = await ac.get("/api/cost/summary", headers=headers)
            elapsed = time.time() - start
            
            # 応答時間が 5 秒以内（CI環境では緩めに設定）
            assert elapsed < 5.0, f"API response too slow: {elapsed:.2f}s"


class TestEdgeCases:
    """エッジケーステスト。"""

    @pytest.mark.asyncio
    async def test_zero_credit_deduction(self):
        """消費額0は成功すること。"""
        async with TestingSessionLocal() as session:
            user = await create_test_user(session, credits=10)
            credit_service = CreditService(session)
            
            result = await credit_service.deduct_credits(
                user_id=user.id,
                amount=0,
                transaction_type="test",
                description="Zero deduction",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_negative_amount_raises_error(self):
        """負の消費額はエラーになること。"""
        async with TestingSessionLocal() as session:
            user = await create_test_user(session, credits=10)
            credit_service = CreditService(session)
            
            with pytest.raises(ValueError) as exc_info:
                await credit_service.deduct_credits(
                    user_id=user.id,
                    amount=-5,
                    transaction_type="test",
                    description="Negative amount",
                )
            assert "消費額は0以上である必要があります" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])