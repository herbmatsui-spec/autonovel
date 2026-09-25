"""
Publishers Package (v5.0 Deprecation Notice)
自動ブラウザ操作によるWeb小説投稿機能は、サイト側のCAPTCHA導入や規約リスク、
高いメンテナンスコストのためv5.0で非推奨（Deprecated）となりました。
今後は PlatformCopyFormatter によるワンクリック整形コピー機能を使用してください。
"""
import warnings

from src.services.publishers.base import (
    PublisherAdapter,
    PublisherCredentials,
    PublishResult,
    PublisherError,
    AuthError,
    RateLimitError,
    ValidationError,
    NetworkError,
    async_retry,
)
from src.services.publishers.narou import NarouPublisher, NarouCredentials
from src.services.publishers.kakuyomu import KakuyomuPublisher, KakuyomuCredentials
from src.services.publishers.kobo import KoboPublisher, KoboCredentials
from src.services.publishers.kindle import KindlePublisher, KindleCredentials
from src.services.publishers.credentials import (
    CredentialStore,
    CredentialConfig,
    get_credential_store,
    create_env_file,
)

# Publisher レジストリ
_PUBLISHERS = {
    NarouPublisher.platform: NarouPublisher,
    KakuyomuPublisher.platform: KakuyomuPublisher,
    KoboPublisher.platform: KoboPublisher,
    KindlePublisher.platform: KindlePublisher,
}

_CREDENTIALS_CLASSES = {
    "narou": NarouCredentials,
    "kakuyomu": KakuyomuCredentials,
    "kobo": KoboCredentials,
    "kindle": KindleCredentials,
}


def get_publisher(platform: str) -> PublisherAdapter:
    """プラットフォーム名からPublisherインスタンスを取得"""
    cls = _PUBLISHERS.get(platform)
    if not cls:
        raise ValueError(f"Unknown publisher: {platform}. Available: {list(_PUBLISHERS.keys())}")
    return cls()


def get_credentials_class(platform: str) -> type[PublisherCredentials]:
    """プラットフォーム名から認証情報クラスを取得"""
    cls = _CREDENTIALS_CLASSES.get(platform)
    if not cls:
        raise ValueError(f"Unknown credentials class for: {platform}")
    return cls()


def list_publishers() -> list[dict[str, str]]:
    """対応Publisher一覧を返す"""
    return [{"platform": p.platform, "description": p.description} for p in _PUBLISHERS.values()]


__all__ = [
    "PublisherAdapter",
    "PublisherCredentials",
    "PublishResult",
    "PublisherError",
    "AuthError",
    "RateLimitError",
    "ValidationError",
    "NetworkError",
    "async_retry",
    "NarouPublisher",
    "NarouCredentials",
    "KakuyomuPublisher",
    "KakuyomuCredentials",
    "KoboPublisher",
    "KoboCredentials",
    "KindlePublisher",
    "KindleCredentials",
    "CredentialStore",
    "CredentialConfig",
    "get_publisher",
    "get_credentials_class",
    "list_publishers",
    "get_credential_store",
    "create_env_file",
]
