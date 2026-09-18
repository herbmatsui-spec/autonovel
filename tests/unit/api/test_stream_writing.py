import pytest
from httpx import AsyncClient, ASGITransport
from src.backend.server import app
from src.backend.auth import get_current_user
from src.backend.database.models import User

@pytest.mark.asyncio
async def test_stream_writing_endpoint():
    transport = ASGITransport(app=app)
    # Create a mock user for testing
    test_user = User(id=1, email="test@example.com", hashed_password="test", display_name="testuser")
    app.dependency_overrides[get_current_user] = lambda: test_user
    
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            from src.backend.routers.stream_writing import router
            # Ensure router is included (safe to call multiple times)
            app.include_router(router)

            # New endpoint signature: /api/stream/writing/{book_id}/{ep_num}?branch_id=1
            resp = await client.get("/api/stream/writing/1/1?branch_id=1")
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            content = resp.text
            assert "ContextBuilding" in content
            assert "Complete" in content
    finally:
        app.dependency_overrides.pop(get_current_user, None)