"""P0 セキュリティ IDOR ガード網羅検証テスト"""
import pytest
from fastapi.testclient import TestClient
from src.backend.server import app
from src.backend.security.jwt import create_access_token
from src.backend.database.models import Base, User, Book
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.backend.database import get_db
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

@pytest.fixture(autouse=True)
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

def test_unauthenticated_export_blocked():
    with TestClient(app) as client:
        resp = client.get("/api/export/books/1")
        assert resp.status_code == 401

def test_cross_user_book_export_forbidden():
    # Create test data: book owned by user 101
    import asyncio
    async def create_data():
        async with TestingSessionLocal() as session:
            # Create users with tenant_id = NULL (allowed)
            user_a = User(id=101, email="a@test.com", hashed_password="hash", display_name="User A", role="user", tenant_id=None)
            user_b = User(id=202, email="b@test.com", hashed_password="hash", display_name="User B", role="user", tenant_id=None)
            session.add_all([user_a, user_b])
            await session.commit()
            await session.refresh(user_a)
            await session.refresh(user_b)
            book = Book(id=1, user_id=101, title="Test Book")
            session.add(book)
            await session.commit()
            await session.refresh(book)
    asyncio.run(create_data())

    token_b = create_access_token(data={"sub": "202", "role": "user"})
    with TestClient(app) as client:
        resp = client.get(
            "/api/export/books/1",
            headers={"Authorization": f"Bearer {token_b}"}
        )
        assert resp.status_code in [403, 404]