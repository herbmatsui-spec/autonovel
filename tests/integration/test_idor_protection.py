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
async def test_user_cannot_access_other_users_book():
    # ユーザーAとユーザーB、およびユーザーBの作品をDBに登録
    async with TestingSessionLocal() as session:
        user_a = User(email="a@test.com", hashed_password="hash", display_name="User A", role="user")
        user_b = User(email="b@test.com", hashed_password="hash", display_name="User B", role="user")
        session.add_all([user_a, user_b])
        await session.commit()
        await session.refresh(user_a)
        await session.refresh(user_b)

        book_b = Book(user_id=user_b.id, title="User B Secret Book")
        session.add(book_b)
        await session.commit()
        await session.refresh(book_b)
        book_b_id = book_b.id
        user_a_id = user_a.id
        user_a_role = user_a.role

    # ユーザーAのトークン生成
    token_a = create_access_token(user_id=user_a_id, role=user_a_role)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # ユーザーAがユーザーBの作品ID をリクエスト
        res = await ac.get(f"/api/books/{book_b_id}", headers=headers_a)
        # 403 Forbidden または 404 Not Found (リソース隠蔽) であることを検証
        assert res.status_code in (403, 404), f"Unexpected status: {res.status_code}"
