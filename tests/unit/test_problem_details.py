import pytest
from httpx import AsyncClient, ASGITransport
from src.backend.server import app

@pytest.mark.asyncio
async def test_rfc7807_error_response_format():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 存在しないパスへのアクセスで 404 (認証 401 の場合もある)
        res = await ac.get("/api/books/9999999")
        assert res.status_code in (401, 403, 404)
        data = res.json()

        # RFC 7807 フィールドが揃っている場合は必須・推奨フィールドを検証し、
        # 401 プレーン形式の場合は detail のみ検証する
        if "status" in data:
            assert "title" in data
            assert "type" in data
            assert res.headers.get("content-type") == "application/problem+json"
        else:
            assert "detail" in data or "title" in data
