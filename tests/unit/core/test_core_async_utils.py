from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.async_utils import (
    fire_and_forget,
    get_concurrency_semaphore,
    limit_concurrency,
    run_parallel,
    safe_timeout,
)


@pytest.mark.asyncio
async def test_run_parallel_success():
    async def task1():
        await asyncio.sleep(0.01)
        return "result1"

    async def task2():
        await asyncio.sleep(0.01)
        return "result2"

    results = await run_parallel([task1(), task2()])
    assert results == ["result1", "result2"]


@pytest.mark.asyncio
async def test_run_parallel_return_exceptions():
    async def task_ok():
        return "ok"

    async def task_err():
        raise ValueError("simulated error")

    results = await run_parallel([task_ok(), task_err()], return_exceptions=True)
    assert results[0] == "ok"
    assert isinstance(results[1], ValueError)
    assert str(results[1]) == "simulated error"


@pytest.mark.asyncio
async def test_run_parallel_raise_on_exception():
    async def task_ok():
        await asyncio.sleep(0.05)
        return "ok"

    async def task_err():
        raise RuntimeError("boom")

    with pytest.raises(ExceptionGroup):
        await run_parallel([task_ok(), task_err()], return_exceptions=False)


@pytest.mark.asyncio
async def test_safe_timeout_success():
    async with safe_timeout(0.5):
        await asyncio.sleep(0.01)
    # Success without raising


@pytest.mark.asyncio
async def test_safe_timeout_exceeded():
    with pytest.raises(TimeoutError):
        async with safe_timeout(0.02):
            await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_fire_and_forget_success():
    executed = False

    async def bg_work():
        nonlocal executed
        await asyncio.sleep(0.01)
        executed = True

    task = fire_and_forget(bg_work(), name="test_bg_success")
    assert isinstance(task, asyncio.Task)
    await task
    assert executed is True


@pytest.mark.asyncio
async def test_fire_and_forget_error():
    async def bg_fail():
        raise ValueError("bg failure")

    with patch("src.core.async_utils.logger.exception") as mock_log:
        task = fire_and_forget(bg_fail(), name="test_bg_fail")
        await asyncio.sleep(0.05)
        mock_log.assert_called_once()
        assert "Background task test_bg_fail failed" in mock_log.call_args[0][0]


@pytest.mark.asyncio
async def test_limit_concurrency():
    sem = asyncio.Semaphore(2)

    with patch("src.core.async_utils.get_concurrency_semaphore", return_value=sem):
        async def work():
            await asyncio.sleep(0.01)
            return "done"

        result = await limit_concurrency(work())
        assert result == "done"
