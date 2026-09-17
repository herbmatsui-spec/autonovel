import pytest
from httpx import AsyncClient, ASGITransport
from src.backend.server import app

@pytest.mark.asyncio
async def test_stream_writing_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        from src.backend.routers.stream_writing import router
        # Ensure router is included (safe to call multiple times)
        app.include_router(router)

        resp = await client.get("/api/stream/writing/1")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        content = resp.text
        assert "ContextBuilding" in content
        assert "Complete" in content