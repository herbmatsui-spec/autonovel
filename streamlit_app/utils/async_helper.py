"""
streamlit_app/utils/async_helper.py — 非同期処理実行ヘルパー
"""
import asyncio
import functools
import logging
from typing import Any, Callable, Coroutine, TypeVar, cast

logger = logging.getLogger(__name__)

T = TypeVar("T")

def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """
    同期コンテキストから非同期コルーチンを実行し、結果を返す。
    Streamlitのような同期的なイベントループを持つ環境で安全にasyncioを動作させる。
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # すでにループが動いている場合は、現在のスレッドで同期的に待機させることはできないため
        # ここでは簡易的に new_event_loop を検討するか、
        # 実際には streamlit の実行環境に合わせて適切に処理する。
        # 通常の streamlit アプリケーションでは、ここで asyncio.run() のような挙動を模倣する。
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return loop.run_until_complete(coro)

def async_to_sync(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """
    非同期関数を同期関数に変換するデコレータ。
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        return run_async(func(*args, **kwargs))
    return cast(Callable[..., T], wrapper)
