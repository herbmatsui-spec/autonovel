import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from src.backend.server import app
from src.backend.database import get_db
from src.backend.database.models import Base, User, Book
from src.backend.security.jwt import create_access_token
from src.backend.security.password import hash_password
from src.core.container import AppContainer


# テスト用インメモリSQLite
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # AppContainer の db をテスト用セッションファクトリに差し替え
    original_db = AppContainer.db
    AppContainer.db = TestingSessionLocal
    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.pop(get_db, None)
    AppContainer.db = original_db
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def alice_token():
    async with TestingSessionLocal() as session:
        alice = User(
            email="alice@example.com",
            hashed_password=hash_password("password123"),
            display_name="Alice Author",
            role="user",
            status="active",
            credits=100,
        )
        session.add(alice)
        await session.commit()
        await session.refresh(alice)
        return create_access_token(alice.id, alice.role)


@pytest_asyncio.fixture
async def bob_token():
    async with TestingSessionLocal() as session:
        bob = User(
            email="bob@example.com",
            hashed_password=hash_password("password123"),
            display_name="Bob Reader",
            role="user",
            status="active",
            credits=50,
        )
        session.add(bob)
        await session.commit()
        await session.refresh(bob)
        return create_access_token(bob.id, bob.role)


@pytest.mark.asyncio
async def test_multitenancy_isolation(alice_token, bob_token):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Aliceが作品を作成
        resp = await ac.post(
            "/api/books",
            json={"title": "Alice Story", "genre": "ファンタジー"},
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        assert resp.status_code == 200, resp.text
        book_id = resp.json()["id"]

        # 2. Alice本人は作品を取得できる
        resp_alice = await ac.get(
            f"/api/books/{book_id}",
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        assert resp_alice.status_code == 200
        assert resp_alice.json()["title"] == "Alice Story"

        # 3. BobがAliceの作品にアクセスを試みると 403 Forbidden
        resp_bob = await ac.get(
            f"/api/books/{book_id}",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert resp_bob.status_code == 403

        # 4. Bobの作品一覧にAliceの作品が含まれないことを確認
        resp_bob_list = await ac.get(
            "/api/books",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert resp_bob_list.status_code == 200
        assert book_id not in [b["id"] for b in resp_bob_list.json()]

        # 5. Aliceの作品一覧には含まれることを確認
        resp_alice_list = await ac.get(
            "/api/books",
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        assert resp_alice_list.status_code == 200
        assert book_id in [b["id"] for b in resp_alice_list.json()]
