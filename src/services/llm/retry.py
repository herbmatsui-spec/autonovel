"""LLM API 呼び出し用の指数バックオフリトライヘルパー。"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)


async def with_retry[T](
    async_func: Callable[[], Coroutine[Any, Any, T]],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> T:
    """非同期関数を指数バックオフでリトライ実行する。"""
    delay = initial_delay
    last_exception: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            return await async_func()
        except Exception as exc:
            last_exception = exc
            if attempt == max_retries:
                logger.error("All %d retries failed. Last error: %s", max_retries, exc)
                break
            logger.warning(
                "LLM call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                attempt,
                max_retries,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
            delay *= backoff_factor

    if last_exception:
        raise last_exception
    raise RuntimeError("Retry loop exited unexpectedly without result or exception.")
