"""バックエンド共通のドメイン例外。"""

from typing import Optional


class BackendError(Exception):
    """すべてのバックエンド例外の基底。"""

    def __init__(self, message: str, *, cause: Optional[BaseException] = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause


class RateLimitExceeded(BackendError):
    """レート制限を超過した。"""


class CacheError(BackendError):
    """Redis/キャッシュ操作の失敗。"""


class CacheMiss(BackendError):
    """キャッシュにキーが存在しない。"""


class DatabaseError(BackendError):
    """DB 操作中の失敗。"""
