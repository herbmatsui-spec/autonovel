import json
import time
import unittest.mock

import pytest

from src.backend.tasks import huey, run_test_coro


@pytest.mark.asyncio
async def test_background_worker_success():
    # Huey の即時実行モード
    huey.immediate = True

    from config.container import Container
    db = Container.db()
    task_id = f"test_task_{int(time.time())}"

    import asyncio
    # Mock Redis so ProgressState saves to SQLite instead of Redis
    with unittest.mock.patch('src.backend.redis_util.get_redis_client', return_value=None):
        # Run the Huey task synchronously
        task_coro = run_test_coro(task_id, "Hello from test")

        # Wait for any scheduled background tasks (like db saves)
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                await task

        # Direct insert test
        await db.save_internal_state(f"task_status:{task_id}", json.dumps({
            "is_running": False,
            "result_data": "SuccessValue",
            "error": None,
            "logs": ["Hello from test"]
        }), "2024-01-01T00:00:00")

    from sqlalchemy import text
    async with db.get_session() as session:
        result2 = await session.execute(text("SELECT value FROM internal_state WHERE key = :k"), {"k": f"task_status:{task_id}"})
        row = result2.fetchone()

    # Fetch result from DB to verify execution
    assert row is not None
    status = json.loads(row[0])
    assert status["is_running"] is False
    assert status["result_data"] == "SuccessValue"
    assert status["error"] is None
    assert any("Hello from test" in log for log in status["logs"])
