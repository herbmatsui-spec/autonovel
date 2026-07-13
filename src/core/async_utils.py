import asyncio
from contextlib import asynccontextmanager
from typing import Any, Coroutine, Iterable, Sequence, TypeVar

T = TypeVar("T")

async def run_parallel(
    coroutines: Iterable[Coroutine[Any, Any, T]],
    return_exceptions: bool = False
) -> Sequence[T]:
    """
    asyncio.TaskGroup を使用してコルーチンのリストを並行して実行し、結果を返します。
    
    Python 3.11+ の TaskGroup をラップし、gather のようなインターフェースを提供します。
    
    Args:
        coroutines: 実行するコルーチンのイテラブル。
        return_exceptions: True の場合、例外を結果として返し、他のタスクを継続させます。
                                False の場合、一つの例外で全タスクがキャンセルされます。
    
    Returns:
        実行結果のリスト。
    """
    results = []
    tasks = []

    async with asyncio.TaskGroup() as tg:
        for coro in coroutines:
            # return_exceptions=True の場合は、個別のタスクで例外をキャプチャするラッパーを被せる
            if return_exceptions:
                async def _wrap(c=coro):
                    try:
                        return await c
                    except Exception as e:
                        return e
                task = tg.create_task(_wrap())
            else:
                task = tg.create_task(coro)
            tasks.append(task)


@asynccontextmanager
async def safe_timeout(seconds: float):
    """
    asyncio.timeout (Python 3.11+) を使用した安全なタイムアウト管理。
    
    Args:
        seconds: タイムアウト秒数。
    """
    try:
        async with asyncio.timeout(seconds):
            yield
    except asyncio.TimeoutError:
        logger.warning(f"Async operation timed out after {seconds} seconds")
        raise

async def fire_and_forget(coro: Coroutine[Any, Any, Any], name: str = "bg_task"):
    """
    構造化並行性の外でバックグラウンドタスクを安全に起動するためのヘルパー。
    エラーハンドリングを強制し、放置されたタスクによるサイレントフェイルを防ぎます。
    """
    task = asyncio.create_task(coro, name=name)

    def _handle_done(t: asyncio.Task):
        try:
            t.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception(f"Background task {name} failed: {e}")

    task.add_done_callback(_handle_done)
    return task

_concurrency_semaphore = asyncio.Semaphore(5)

async def limit_concurrency(coro: Coroutine[Any, Any, T]) -> T:
    """
    グローバルセマフォを使用して同時に実行されるAPIリクエスト等の数を制限します。
    """
    async with _concurrency_semaphore:
        return await coro
