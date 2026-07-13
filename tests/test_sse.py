import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_sse_endpoint_no_task(monkeypatch):
    """
    タスクが存在しない、または無効な場合のSSEストリームの挙動を確認する。
    """
    fd, temp_db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    db_url = f'sqlite+aiosqlite:///{temp_db_path}'
    monkeypatch.setattr('config.DATABASE_URL', db_url)
    monkeypatch.setattr('config.base.DATABASE_URL', db_url)

    from src.backend.database.core import set_db_manager
    set_db_manager(None)

    from src.backend.server import app

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            async with ac.stream("GET", "/api/tasks/non_existent_task/stream") as stream_response:
                assert stream_response.status_code == 200
                assert "text/event-stream" in stream_response.headers["content-type"]
    finally:
        set_db_manager(None)
        try:
            os.unlink(temp_db_path)
        except PermissionError:
            pass
