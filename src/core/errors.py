"""
core/errors.py - 統一エラーハンドリングモデルとデコレータ
"""

from typing import TypeVar, Generic, Optional, Dict, Any
import traceback
import logging

T = TypeVar('T')


class AgentResult(Generic[T]):
    """エージェントの実行結果を表すジェネリッククラス。
    成功時は data に値、失敗時は error に例外またはエラーメッセージを格納。
    """

    def __init__(self, *, success: bool, data: Optional[T] = None, error: Optional[Any] = None):
        self.success = success
        self.data = data
        self.error = error

    @classmethod
    def ok(cls, data: T) -> 'AgentResult[T]':
        return cls(success=True, data=data, error=None)

    @classmethod
    def err(cls, error: Any) -> 'AgentResult[None]':
        return cls(success=False, data=None, error=error)

    def is_success(self) -> bool:
        return self.success

    def unwrap(self) -> T:
        if not self.success:
            raise self.error if isinstance(self.error, Exception) else RuntimeError(str(self.error))
        return self.data  # type: ignore

    def unwrap_err(self) -> Any:
        if self.success:
            raise RuntimeError("Result is success, no error to unwrap")
        return self.error

    def __repr__(self) -> str:
        if self.success:
            return f"AgentResult.ok(data={self.data!r})"
        else:
            return f"AgentResult.err(error={self.error!r})"


def handle_error(logger_name: str = None):
    """エージェントのメソッドに適用するデコレータ。
    例外を捕捉し、AgentResult.err に変換してロギングする。
    デコレータ対象のメソッドは AgentResult[T] を返すことが期待される。
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(logger_name or func.__module__)
            try:
                result = func(*args, **kwargs)
                # もし結果がすでに AgentResult ならそのまま返す
                if isinstance(result, AgentResult):
                    return result
                # それ以外は成功とみなしてラップ
                return AgentResult.ok(result)
            except Exception as e:
                logger.exception(f"Exception in {func.__name__}: {e}")
                return AgentResult.err(e)

        # 非同期関数もサポート
        import asyncio
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                logger = logging.getLogger(logger_name or func.__module__)
                try:
                    result = await func(*args, **kwargs)
                    if isinstance(result, AgentResult):
                        return result
                    return AgentResult.ok(result)
                except Exception as e:
                    logger.exception(f"Exception in {func.__name__}: {e}")
                    return AgentResult.err(e)

            return async_wrapper
        else:
            return wrapper

    return decorator