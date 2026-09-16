"""実DBセッションを用いた get_current_user の単体テスト"""
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import src.backend.database.models_tenant  # noqa: F401  (Tenant FK 解決のため必須)
from src.backend.database.models import Base, User
from src.backend.auth import get_current_user
from src.backend.security.jwt import create_access_token

@pytest_asyncio.fixture
async def real_db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = async_session()
    test_user = User(
        id=101,
        email="test_real@example.com",
        hashed_password="dummy",
        display_name="Test Real User",
        role="user",
        status="active",
        plan_tier="free",
        credits=100,
    )
    session.add(test_user)
    await session.commit()
    await session.refresh(test_user)
    yield session
    await session.close()
    await engine.dispose()

@pytest.mark.asyncio
async def test_get_current_user_with_real_session_no_await_error(real_db_session):
    token = create_access_token(data={"sub": "101", "role": "user"})
    user = await get_current_user(token=token, db=real_db_session)
    assert user.id == 101
    assert user.email == "test_real@example.com"
