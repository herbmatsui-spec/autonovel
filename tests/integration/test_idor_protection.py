import pytest
from httpx import AsyncClient, ASGITransport
from src.backend.server import app
from src.backend.database.models import User, Book
from src.backend.security.jwt import create_access_token

@pytest.mark.asyncio
async def test_user_cannot_access_other_users_book(monkeypatch):
    user_a = User(id=1, role="user", email="a@test.com")
    user_b = User(id=2, role="user", email="b@test.com")
    book_b = Book(id=50, user_id=2, title="User B Secret Book")

    # 認証トークン生成
    token_a = create_access_token(user_id=user_a.id, role=user_a.role)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # ユーザーAがユーザーBの作品ID 50 をリクエスト
        res = await ac.get("/api/books/50", headers=headers_a)
        # 403 Forbidden または 404 Not Found (リソース隠蔽) であることを検証
        assert res.status_code in (403, 404), f"Unexpected status: {res.status_code}"
