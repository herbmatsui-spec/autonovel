import asyncio

import pytest

from src.core.observability import TraceContext


@pytest.mark.asyncio
async def test_trace_context_isolation():
    """
    異なる非同期タスク間で Trace ID が独立して保持されることを検証するテスト。
    """
    print("Starting TraceContext isolation test...")

    async def task_worker(name: str, tid: str):
        # トレースIDをセット
        TraceContext.set_trace_id(tid)
        # 少し待機してコンテキストの切り替えを誘発
        await asyncio.sleep(0.1)
        # セットしたIDが保持されているか確認
        current_id = TraceContext.get_trace_id()
        print(f"Worker {name}: expected={tid}, actual={current_id}")
        assert current_id == tid

    # 複数のタスクを並列に実行
    await asyncio.gather(
        task_worker("A", "trace-aaa"),
        task_worker("B", "trace-bbb"),
        task_worker("C", "trace-ccc"),
    )

    # 全てのタスク終了後、トレースIDが独立していることを確認
    TraceContext.clear()
    current_after_clear = TraceContext.get_trace_id()
    print(f"After clear: {current_after_clear}")
    assert isinstance(current_after_clear, str)
    assert len(current_after_clear) > 0

    print("TraceContext isolation test passed!")


@pytest.mark.asyncio
async def test_trace_context_set_clear_isolation():
    """
    set_trace_id / clear が非同期コンテキストごとに独立して効くことを検証するテスト。
    """
    results = {}

    async def task_worker(name: str, tid: str):
        TraceContext.set_trace_id(tid)
        await asyncio.sleep(0.05)
        results[name] = TraceContext.get_trace_id()

    await asyncio.gather(
        task_worker("X", "trace-xxx"),
        task_worker("Y", "trace-yyy"),
    )

    assert results["X"] == "trace-xxx"
    assert results["Y"] == "trace-yyy"

    # メインコンテキストは影響を受けない
    TraceContext.clear()
    main_id = TraceContext.get_trace_id()
    assert isinstance(main_id, str)
    assert len(main_id) > 0


if __name__ == "__main__":
    asyncio.run(test_trace_context_isolation())
