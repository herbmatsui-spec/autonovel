"""Server-Sent Events (SSE) 執筆ストリーミングAPIの単体テスト (v5.0 Step 22)."""
import pytest
from httpx import AsyncClient, ASGITransport
from src.backend.server import app


@pytest.mark.asyncio
async def test_stream_writing_endpoint(monkeypatch):
    from src.backend.config import settings

    monkeypatch.setattr(settings, "AUTH_DISABLED", True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/stream/writing/1")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        content = resp.text
        assert "ContextBuilding" in content
        assert "Complete" in content

