import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.backend.server import app
from src.backend.database import get_db
from src.backend.database.models import Base, User, Book
from src.backend.security.jwt import create_access_token
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
async def test_unauthenticated_requests_are_rejected():
    """認証ヘッダーなしのリクエストが各ドメインエンドポイントで確実に拒絶されることを検証"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. /admin/anti_ai
        res = await ac.post("/admin/anti_ai/detect", json={"text": "Hello"})
        assert res.status_code in (401, 403), res.status_code

        # 2. /api/cost/summary
        res = await ac.get("/api/cost/summary")
        assert res.status_code == 401

        # 3. /api/plots/1
        res = await ac.get("/api/plots/1")
        assert res.status_code == 401

        # 4. /api/trace/books/1/runs
        res = await ac.get("/api/trace/books/1/runs")
        assert res.status_code == 401

        # 5. /commercial/schedules/1
        res = await ac.get("/commercial/schedules/1")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_cross_tenant_isolation_on_plots_and_trace():
    """Aliceの作品に対してBobがアクセスを試行した際に403 Forbiddenで遮断されることを検証"""
    async with TestingSessionLocal() as session:
        alice = User(email="alice@example.com", hashed_password="pw", display_name="Alice", role="user", status="active")
        bob = User(email="bob@example.com", hashed_password="pw", display_name="Bob", role="user", status="active")
        session.add_all([alice, bob])
        await session.commit()
        await session.refresh(alice)
        await session.refresh(bob)

        alice_book = Book(user_id=alice.id, title="Alice Secret Book")
        session.add(alice_book)
        await session.commit()
        await session.refresh(alice_book)

    alice_token = create_access_token(alice.id, alice.role)
    bob_token = create_access_token(bob.id, bob.role)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Alice本人はプロット一覧を取得可能 (200)
        res_alice = await ac.get(
            f"/api/plots/{alice_book.id}",
            headers={"Authorization": f"Bearer {alice_token}"},
        )
        assert res_alice.status_code == 200

        # BobがAliceの作品のプロットを取得しようとすると 403 Forbidden
        res_bob = await ac.get(
            f"/api/plots/{alice_book.id}",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert res_bob.status_code == 403

        # BobがAliceの作品の生成トレースを取得しようとすると 403 Forbidden
        res_bob_trace = await ac.get(
            f"/api/trace/books/{alice_book.id}/runs",
            headers={"Authorization": f"Bearer {bob_token}"},
        )
        assert res_bob_trace.status_code == 403
