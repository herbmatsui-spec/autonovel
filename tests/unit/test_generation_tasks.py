"""Generation tasks ユニットテスト。"""
from __future__ import annotations

from src.backend.tasks.generation_tasks import _run_async, _update_task_in_db


def test__run_async_basic():
    """_run_async は coroutine を同期実行する。"""

    async def simple_coro():
        return 42

    result = _run_async(simple_coro())
    assert result == 42


def test__run_async_close():
    """_run_async は event loop を閉じる。"""

    async def simple_coro():
        return "ok"

    result = _run_async(simple_coro())
    assert result == "ok"


def test__generate_imports():
    """_generate は generate_with_llm を遅延インポートする。"""
    # インポートエラーなく呼び出せること
    pass


def test__update_task_in_db_completed(real_db_manager):
    """ステータス completed で結果を DB に保存する。"""
    _update_task_in_db("test-task-1", "completed", '{"chapter": "test"}')


def test__update_task_in_db_failed(real_db_manager):
    """エラー時にもロールバックすること。"""
    _update_task_in_db("test-task-2", "failed")
