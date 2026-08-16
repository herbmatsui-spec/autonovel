import asyncio
import functools
import warnings


def run_async(coro):
    """同期コンテキストから非同期関数を実行するためのラッパー

    非推奨: asyncio.run() を直接使用してください。
    """
    warnings.warn(
        "run_async is deprecated. Use asyncio.run() directly.",
        DeprecationWarning,
        stacklevel=2,
    )
    return asyncio.run(coro)


def async_task(func):
    """非同期関数を同期的に呼び出せるようにするデコレータ

    非推奨: 非同期関数を直接 await してください。
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            "async_task is deprecated. Await the async function directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        return run_async(func(*args, **kwargs))

    return wrapper
