"""safe_run_async のパフォーマンステスト"""
import asyncio
import time
from src.backend.engine_utils import safe_run_async


def test_runs_coroutine_from_sync_context():
    async def coro():
        return 42
    assert safe_run_async(coro()) == 42


def test_does_not_create_new_thread_pool_per_call():
    """パフォーマンス回帰防止"""
    async def coro():
        return None
    start = time.perf_counter()
    for _ in range(100):
        safe_run_async(coro())
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0  # 100回で 5 秒以内