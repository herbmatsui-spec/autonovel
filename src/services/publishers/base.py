"""
src/services/publishers/base.py - Publisher Adapter 基底クラス

各プラットフォーム（なろう/カクヨム/Kobo/Kindle）への投稿インターフェースを定義。
"""

from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from functools import wraps


@dataclass
class PublishResult:
    """投稿結果を表すデータクラス"""

    success: bool
    platform: str
    post_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PublisherCredentials:
    """プラットフォーム別認証情報の基底クラス"""

    platform: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


class PublisherError(Exception):
    """Publisher基底例外"""

    def __init__(self, message: str, platform: str, recoverable: bool = False):
        super().__init__(message)
        self.platform = platform
        self.recoverable = recoverable


class AuthError(PublisherError):
    """認証エラー（リカバリ不可）"""

    def __init__(self, message: str, platform: str):
        super().__init__(message, platform, recoverable=False)


class RateLimitError(PublisherError):
    """レート制限エラー（リカバリ可能）"""

    def __init__(self, message: str, platform: str, retry_after: Optional[float] = None):
        super().__init__(message, platform, recoverable=True)
        self.retry_after = retry_after


class ValidationError(PublisherError):
    """バリデーションエラー（リカバリ不可）"""

    def __init__(self, message: str, platform: str):
        super().__init__(message, platform, recoverable=False)


class NetworkError(PublisherError):
    """ネットワークエラー（リカバリ可能）"""

    def __init__(self, message: str, platform: str):
        super().__init__(message, platform, recoverable=True)


class PublisherAdapter(ABC):
    """Publisher アダプタの基底抽象クラス"""

    platform: str = "base"
    description: str = ""

    # レート制限設定（サブクラスでオーバーライド）
    rate_limit_per_minute: int = 30
    rate_limit_per_hour: int = 500

    def __init__(self):
        self._session_cookies: dict[str, str] = {}
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[float] = None

    @abstractmethod
    async def authenticate(self, credentials: PublisherCredentials) -> bool:
        """
        プラットフォームへの認証を実行する。

        Args:
            credentials: 認証情報

        Returns:
            認証成功時True

        Raises:
            AuthError: 認証失敗時
        """
        ...

    @abstractmethod
    async def publish(
        self, novel: dict[str, Any], chapter: dict[str, Any], credentials: PublisherCredentials
    ) -> PublishResult:
        """
        新規投稿を実行する。

        Args:
            novel: 小説メタデータ（title, synopsis, tags等）
            chapter: エピソードデータ（ep_num, title, content等）
            credentials: 認証情報

        Returns:
            投稿結果
        """
        ...

    @abstractmethod
    async def update_chapter(
        self, post_id: str, chapter: dict[str, Any], credentials: PublisherCredentials
    ) -> PublishResult:
        """
        既存投稿の更新（次話追加等）を実行する。

        Args:
            post_id: プラットフォーム側の投稿ID
            chapter: 更新するエピソードデータ
            credentials: 認証情報

        Returns:
            更新結果
        """
        ...

    @abstractmethod
    async def get_post_status(
        self, post_id: str, credentials: PublisherCredentials
    ) -> dict[str, Any]:
        """
        投稿ステータスを取得する。

        Args:
            post_id: プラットフォーム側の投稿ID
            credentials: 認証情報

        Returns:
            ステータス情報（公開状態、閲覧数等）
        """
        ...

    async def _apply_rate_limit(self) -> None:
        """レート制限を考慮した待機（サブクラスで実装推奨）"""
        await asyncio.sleep(60 / self.rate_limit_per_minute)

    def _build_novel_payload(
        self, novel: dict[str, Any], chapter: dict[str, Any]
    ) -> dict[str, Any]:
        """小説・チャプターデータから投稿用ペイロードを構築（共通ロジック）"""
        return {
            "title": novel.get("title", "無題"),
            "synopsis": novel.get("synopsis", ""),
            "chapter_title": chapter.get("title") or f"第{chapter.get('ep_num', 1)}話",
            "content": chapter.get("content", ""),
            "tags": novel.get("tags", []),
            "is_adult": novel.get("is_adult", False),
        }


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: float = 0.1,
    retryable_exceptions: tuple[type[Exception], ...] = (
        RateLimitError,
        NetworkError,
        asyncio.TimeoutError,
    ),
) -> Callable:
    """
    非同期関数に対する指数バックオフリトライデコレータ。

    Args:
        max_attempts: 最大試行回数
        base_delay: 初回待機秒数
        max_delay: 最大待機秒数
        exponential_base: 指数の底
        jitter: ジッター係数（0.0-1.0）
        retryable_exceptions: リトライ対象例外タプル
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as exc:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise

                    # RateLimitErrorの場合はretry_afterを優先使用
                    if isinstance(exc, RateLimitError) and exc.retry_after:
                        delay = exc.retry_after
                        jitter_amount = delay * jitter * random.uniform(0.5, 1.5)
                        total_delay = delay + jitter_amount
                    else:
                        delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                        jitter_amount = delay * jitter * random.uniform(0.5, 1.5)
                        total_delay = delay + jitter_amount

                    await asyncio.sleep(total_delay)
                except Exception:
                    # リトライ対象外の例外は即座に再送出
                    raise

        return wrapper

    return decorator
