import pytest
from httpx import AsyncClient, ASGITransport
from src.backend.server import app

@pytest.mark.asyncio
async def test_rfc7807_error_response_format():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 存在しないパスへのアクセスで 404
        res = await ac.get("/api/books/9999999")
        assert res.status_code in (401, 403, 404)
        data = res.json()
        
        # RFC 7807 の必須・推奨フィールドの存在検証
        assert "status" in data
        assert "title" in data
        assert "type" in data
        assert res.headers.get("content-type") == "application/problem+json"
