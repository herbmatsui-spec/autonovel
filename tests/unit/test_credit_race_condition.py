import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from src.backend.database.models import Base, User
from src.backend.database.models_billing import CreditTransaction
from src.services.billing.credit_service import CreditService, InsufficientCreditsError


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


@pytest.mark.asyncio
async def test_credit_deduct_and_grant_atomic_integrity():
    """残高更新とCreditTransactionが正確に整合し、users.creditsがマスターとして更新されることを検証"""
    async with TestingSessionLocal() as session:
        user = User(
            email="author@example.com",
            hashed_password="pw",
            display_name="Author",
            credits=50,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        service = CreditService(session)

        # 30クレジット消費 -> 残高20
        res = await service.deduct_credits(user.id, 30, "consumption", "Writing ep 1")
        assert res is True
        assert await service.get_balance(user.id) == 20

        # さらに30クレジット消費を試みると残高不足で弾かれる
        with pytest.raises(InsufficientCreditsError):
            await service.deduct_credits(user.id, 30, "consumption", "Writing ep 2")

        # 残高が20のままであること
        assert await service.get_balance(user.id) == 20

        # 100クレジット付与 -> 残高120
        new_bal = await service.grant_credits(user.id, 100, "grant", "Bonus")
        assert new_bal == 120
        assert await service.get_balance(user.id) == 120

        # 取引履歴レコードの検証
        tx_query = select(CreditTransaction).where(CreditTransaction.user_id == user.id).order_by(CreditTransaction.id)
        tx_result = await session.execute(tx_query)
        txs = tx_result.scalars().all()
        assert len(txs) == 2
        assert txs[0].amount == -30
        assert txs[0].balance_after == 20
        assert txs[1].amount == 100
        assert txs[1].balance_after == 120
