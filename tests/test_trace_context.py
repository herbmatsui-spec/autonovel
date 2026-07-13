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

    # 全てのタスク終了後、デフォルトに戻っているか（またはシステム値か）確認
    TraceContext.clear()
    print(f"After clear: {TraceContext.get_trace_id()}")
    assert TraceContext.get_trace_id() == "system"

    print("TraceContext isolation test passed!")


if __name__ == "__main__":
    asyncio.run(test_trace_context_isolation())
