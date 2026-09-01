"""
services/errors.py - 覇権AIエンジン例外定義モジュール
後方互換性のため re-export。新規コードは src.core.exceptions を直接使用すること。
"""

import asyncio
import functools
import logging
from collections.abc import Callable

from sqlalchemy.exc import OperationalError

from src.core.exceptions import (
    APIError,
    AppError,
    EngineError,
    HegemonyError,
    LLMError,
    LLMTemporaryError,
    LLMTokenLimitError,
    LLMUnrecoverableError,
    LLMValidationError,
    PipelineError,
    ValidationError,
)

logger = logging.getLogger(__name__)

__all__ = [
    "retry_on_lock",
    "HegemonyError",
    "EngineError",
    "LLMError",
    "LLMTemporaryError",
    "LLMTokenLimitError",
    "LLMValidationError",
    "LLMUnrecoverableError",
    "APIError",
    "AppError",
    "ValidationError",
    "PipelineError",
]


class StreamlitErrorHandler:
    """Streamlit UI 層専用のエラーハンドラ。コアロジックからは import しないこと。"""

    @staticmethod
    def show(error: Exception, context: str = "不明なエラー"):
        import streamlit as st

        logging.error(f"Error in {context}: {error}", exc_info=True)
        st.error(f"❌ {context}: {str(error)}")

    @staticmethod
    def show_connection_error():
        import streamlit as st

        st.warning(
            "⚠️ **バックエンドサーバーに接続できません。**\n"
            "サーバーが起動しているか確認してください。",
            icon="🚨",
        )


def retry_on_lock(retries: int = 10, base_delay: float = 0.1, max_delay: float = 10.0):
    """
    SQLiteの 'database is locked' エラー (OperationalError) に対して
    指数バックオフを用いたリトライを行うデコレータ。
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for i in range(retries):
                try:
                    return await func(*args, **kwargs)
                except OperationalError as e:
                    last_exception = e
                    # 'database is locked' または 'disk I/O error' などのロック関連エラーか確認
                    error_msg = str(e).lower()
                    if "locked" in error_msg or "busy" in error_msg:
                        delay = min(base_delay * (2**i), max_delay)
                        logger.warning(
                            f"Database locked in {func.__name__}. "
                            f"Retry {i + 1}/{retries} after {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        # ロック以外のOperationalErrorは即座に再送出
                        raise e
                except Exception as e:
                    # その他の例外はリトライせずに再送出
                    raise e

            logger.error(
                f"Max retries reached in {func.__name__} due to database lock: {last_exception}"
            )
            raise last_exception

        return wrapper

    return decorator
