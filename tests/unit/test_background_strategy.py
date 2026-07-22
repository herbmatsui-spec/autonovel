import datetime
import json
import unittest.mock

import pytest

from src.backend.background import (
    AsyncDbSaveStrategy,
    ProgressState,
    RedisSaveStrategy,
    SaveStrategy,
    SyncDbSaveStrategy,
    _select_strategy,
)


class DummyRepo:
    class AsyncDummyDB:
        async def save_internal_state(self, key, value, updated_at):
            pass

    def __init__(self):
        self.db = self.AsyncDummyDB()


def test_redis_save_strategy_success():
    state = unittest.mock.Mock()
    state.task_id = "task-1"
    state_json = json.dumps({"is_running": True})

    redis_mock = unittest.mock.Mock()
    with unittest.mock.patch("src.backend.redis_util.get_redis_client", return_value=redis_mock):
        strategy = RedisSaveStrategy()
        strategy.save(state, state_json, "2024-01-01T00:00:00")

    redis_mock.set.assert_called_once_with("task_status:task-1", state_json, ex=86400)
    redis_mock.publish.assert_called_once_with("task_events:task-1", state_json)


def test_redis_save_strategy_unavailable():
    state = unittest.mock.Mock()
    state.task_id = "task-1"
    state_json = json.dumps({"is_running": True})

    with unittest.mock.patch("src.backend.redis_util.get_redis_client", return_value=None):
        strategy = RedisSaveStrategy()
        with pytest.raises(RuntimeError, match="Redis client is not available"):
            strategy.save(state, state_json, "2024-01-01T00:00:00")


@pytest.mark.asyncio
async def test_async_db_save_strategy_success():
    repo = DummyRepo()
    state = unittest.mock.Mock()
    state.task_id = "task-2"
    state.repo = repo

    strategy = AsyncDbSaveStrategy()
    with unittest.mock.patch("asyncio.get_running_loop") as loop_mock:
        task_mock = unittest.mock.AsyncMock()
        loop_mock.return_value.create_task.return_value = task_mock
        strategy.save(state, "{}", "2024-01-01T00:00:00")
        loop_mock.return_value.create_task.assert_called_once()


def test_async_db_save_strategy_no_loop():
    state = unittest.mock.Mock()
    state.task_id = "task-2"
    state.repo = DummyRepo()

    strategy = AsyncDbSaveStrategy()
    with unittest.mock.patch("asyncio.get_running_loop", side_effect=RuntimeError("no running loop")):
        with pytest.raises(RuntimeError, match="No running event loop"):
            strategy.save(state, "{}", "2024-01-01T00:00:00")


def test_sync_db_save_strategy_skips_save():
    state = unittest.mock.Mock()
    state.task_id = "task-3"
    state.repo = DummyRepo()

    strategy = SyncDbSaveStrategy()
    with unittest.mock.patch("asyncio.get_running_loop", side_effect=RuntimeError("no running loop")):
        strategy.save(state, "{}", "2024-01-01T00:00:00")


def test_select_strategy_redis_first():
    state = unittest.mock.Mock()
    state.repo = unittest.mock.Mock()

    redis_mock = unittest.mock.Mock()
    with unittest.mock.patch("src.backend.redis_util.get_redis_client", return_value=redis_mock):
        strategy = _select_strategy(state)
        assert isinstance(strategy, RedisSaveStrategy)


def test_select_strategy_falls_back_to_async_db():
    state = unittest.mock.Mock()
    state.repo = unittest.mock.Mock()
    state.repo.db = unittest.mock.AsyncMock()

    with unittest.mock.patch("src.backend.redis_util.get_redis_client", return_value=None):
        with unittest.mock.patch("asyncio.get_running_loop", return_value=unittest.mock.Mock()):
            strategy = _select_strategy(state)
            assert isinstance(strategy, AsyncDbSaveStrategy)


def test_select_strategy_falls_back_to_sync_db():
    state = unittest.mock.Mock()
    state.repo = unittest.mock.Mock()

    with unittest.mock.patch("src.backend.redis_util.get_redis_client", return_value=None):
        with unittest.mock.patch("asyncio.get_running_loop", side_effect=RuntimeError("no running loop")):
            strategy = _select_strategy(state)
            assert isinstance(strategy, SyncDbSaveStrategy)
