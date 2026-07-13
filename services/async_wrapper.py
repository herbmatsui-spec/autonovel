import asyncio
import functools


def run_async(coro):
    """同期コンテキストから非同期関数を実行するためのラッパー"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

def async_task(func):
    """非同期関数を同期的に呼び出せるようにするデコレータ"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return run_async(func(*args, **kwargs))
    return wrapper

