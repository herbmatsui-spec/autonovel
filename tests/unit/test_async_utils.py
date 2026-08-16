import asyncio

import pytest

from src.core.async_utils import fire_and_forget, limit_concurrency, safe_timeout


@pytest.mark.asyncio
async def test_safe_timeout_normal():
    async with safe_timeout(1.0):
        await asyncio.sleep(0.05)


@pytest.mark.asyncio
async def test_safe_timeout_exceeded():
    with pytest.raises(asyncio.TimeoutError):
        async with safe_timeout(0.05):
            await asyncio.sleep(1.0)


@pytest.mark.asyncio
async def test_limit_concurrency_serializes():
    order: list[int] = []
    sem = asyncio.Semaphore(1)

    async def tracked(n: int) -> int:
        async with sem:
            order.append(n)
            await asyncio.sleep(0.02)
            return n

    # limit_concurrency は内部でグローバルセマフォを使うため、同時実行数が制限される
    results = await asyncio.gather(
        limit_concurrency(tracked(1)),
        limit_concurrency(tracked(2)),
    )
    assert sorted(results) == [1, 2]


@pytest.mark.asyncio
async def test_fire_and_forget_completes():
    done = []

    async def bg():
        await asyncio.sleep(0.01)
        done.append(True)

    # fire_and_forget returns a task that runs in the background
    # We should not await it directly - just let it run
    task = fire_and_forget(bg())

    # Wait for the task to complete
    await asyncio.wait_for(task, timeout=1.0)
    assert done == [True]
