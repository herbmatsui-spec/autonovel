"""
src/services/publishers/kakuyomu.py - カクヨム Publisher

カクヨム非公式REST APIを使用。
公式APIドキュメント: https://kakuyomu.jp/help/api
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from src.services.publishers.base import (
    PublisherAdapter,
    PublisherCredentials,
    PublishResult,
    AuthError,
    RateLimitError,
    ValidationError,
    NetworkError,
    async_retry,
)

logger = logging.getLogger(__name__)


@dataclass
class KakuyomuCredentials(PublisherCredentials):
    """カクヨム認証情報"""

    api_token: str = ""  # カクヨムAPIトークン（マイページ > 設定 > API設定で取得）
    user_id: str = ""  # ユーザーID

    def __post_init__(self):
        self.platform = "kakuyomu"


class KakuyomuPublisher(PublisherAdapter):
    """カクヨム 投稿アダプタ（非公式REST API）"""

    platform = "kakuyomu"
    description = "カクヨム（非公式REST API）"

    rate_limit_per_minute: int = 30
    rate_limit_per_hour: int = 500

    # API エンドポイント
    API_BASE = "https://api.kakuyomu.jp/v1"
    # 代替: 非公式エンドポイント（Web画面と同じAPI）
    WEB_API_BASE = "https://kakuyomu.jp/api"

    def __init__(self, timeout: float = 30.0):
        super().__init__()
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        """HTTPクライアントを遅延初期化"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "User-Agent": "AutoNovel/1.0 (+https://github.com/autonovel)",
                    "Accept": "application/json",
                },
            )
        return self._client

    async def _close_client(self):
        """HTTPクライアントをクローズ"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _get_auth_headers(self, credentials: KakuyomuCredentials) -> dict[str, str]:
        """認証ヘッダー生成"""
        return {
            "Authorization": f"Bearer {credentials.api_token}",
            "X-Kakuyomu-User-ID": credentials.user_id,
        }

    async def authenticate(self, credentials: KakuyomuCredentials) -> bool:
        """APIトークンで認証確認"""
        if not credentials.api_token:
            raise AuthError("APIトークンが必要です（カクヨム設定 > API設定で取得）", self.platform)

        client = self._get_client()

        try:
            # ユーザー情報取得でトークン検証
            response = await client.get(
                f"{self.API_BASE}/user", headers=self._get_auth_headers(credentials)
            )

            if response.status_code == 401:
                raise AuthError("APIトークンが無効または期限切れです", self.platform)
            elif response.status_code == 403:
                raise AuthError("APIアクセス権限がありません", self.platform)
            elif response.status_code >= 400:
                raise NetworkError(f"認証確認失敗: HTTP {response.status_code}", self.platform)

            user_data = response.json()
            credentials.user_id = user_data.get("id", "")

            logger.info("カクヨム認証成功", extra={"user_id": credentials.user_id})
            return True

        except AuthError:
            raise
        except httpx.RequestError as e:
            logger.exception("カクヨム認証ネットワークエラー")
            raise NetworkError(f"接続エラー: {e}", self.platform)
        except Exception as e:
            logger.exception("カクヨム認証エラー")
            raise AuthError(f"認証中にエラーが発生しました: {e}", self.platform)

    @async_retry(max_attempts=3, base_delay=3.0)
    async def publish(
        self, novel: dict[str, Any], chapter: dict[str, Any], credentials: KakuyomuCredentials
    ) -> PublishResult:
        """新規作品投稿（第1話）"""
        client = self._get_client()

        try:
            # 1. 作品作成
            work_payload = {
                "title": novel.get("title", "無題")[:100],
                "synopsis": novel.get("synopsis", "")[:5000],
                "genre": self._map_genre(novel.get("genre", "general")),
                "tags": novel.get("tags", [])[:10],
                "is_adult": novel.get("is_adult", False),
            }

            response = await client.post(
                f"{self.API_BASE}/works",
                headers=self._get_auth_headers(credentials),
                json=work_payload,
            )

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    "レート制限に達しました", self.platform, retry_after=retry_after
                )
            elif response.status_code >= 400:
                error_detail = response.json().get("message", response.text)
                raise ValidationError(f"作品作成失敗: {error_detail}", self.platform)

            work_data = response.json()
            work_id = work_data.get("id")

            if not work_id:
                raise ValidationError("作品IDが返却されませんでした", self.platform)

            # 2. 第1話投稿
            episode_payload = {
                "title": chapter.get("title", "第1話")[:100],
                "body": self._format_for_kakuyomu(chapter.get("content", "")),
                "number": 1,
            }

            response = await client.post(
                f"{self.API_BASE}/works/{work_id}/episodes",
                headers=self._get_auth_headers(credentials),
                json=episode_payload,
            )

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    "レート制限に達しました", self.platform, retry_after=retry_after
                )
            elif response.status_code >= 400:
                error_detail = response.json().get("message", response.text)
                raise ValidationError(f"話投稿失敗: {error_detail}", self.platform)

            episode_data = response.json()
            episode_id = episode_data.get("id")

            post_url = f"https://kakuyomu.jp/works/{work_id}/episodes/{episode_id}"

            return PublishResult(
                success=True,
                platform=self.platform,
                post_id=work_id,
                url=post_url,
                metadata={"work_id": work_id, "episode_id": episode_id, "episode_number": 1},
            )

        except (ValidationError, RateLimitError):
            raise
        except httpx.RequestError as e:
            logger.exception("カクヨム投稿ネットワークエラー")
            raise NetworkError(f"接続エラー: {e}", self.platform)
        except Exception as e:
            logger.exception("カクヨム投稿エラー")
            raise NetworkError(f"投稿中にエラーが発生しました: {e}", self.platform)

    @async_retry(max_attempts=3, base_delay=3.0)
    async def update_chapter(
        self, post_id: str, chapter: dict[str, Any], credentials: KakuyomuCredentials
    ) -> PublishResult:
        """既存作品に話を追加"""
        client = self._get_client()
        work_id = post_id  # カクヨムではpost_id = work_id

        try:
            episode_num = chapter.get("ep_num", 1)

            episode_payload = {
                "title": chapter.get("title", f"第{episode_num}話")[:100],
                "body": self._format_for_kakuyomu(chapter.get("content", "")),
                "number": episode_num,
            }

            response = await client.post(
                f"{self.API_BASE}/works/{work_id}/episodes",
                headers=self._get_auth_headers(credentials),
                json=episode_payload,
            )

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    "レート制限に達しました", self.platform, retry_after=retry_after
                )
            elif response.status_code == 404:
                raise ValidationError(f"作品が見つかりません: {work_id}", self.platform)
            elif response.status_code >= 400:
                error_detail = response.json().get("message", response.text)
                raise ValidationError(f"話追加失敗: {error_detail}", self.platform)

            episode_data = response.json()
            episode_id = episode_data.get("id")

            post_url = f"https://kakuyomu.jp/works/{work_id}/episodes/{episode_id}"

            return PublishResult(
                success=True,
                platform=self.platform,
                post_id=work_id,
                url=post_url,
                metadata={
                    "work_id": work_id,
                    "episode_id": episode_id,
                    "episode_number": episode_num,
                },
            )

        except (ValidationError, RateLimitError):
            raise
        except httpx.RequestError as e:
            logger.exception("カクヨム話追加ネットワークエラー")
            raise NetworkError(f"接続エラー: {e}", self.platform)
        except Exception as e:
            logger.exception("カクヨム話追加エラー")
            raise NetworkError(f"話追加中にエラーが発生しました: {e}", self.platform)

    async def get_post_status(
        self, post_id: str, credentials: KakuyomuCredentials
    ) -> dict[str, Any]:
        """作品ステータス取得"""
        client = self._get_client()

        try:
            # 作品情報取得
            response = await client.get(
                f"{self.API_BASE}/works/{post_id}", headers=self._get_auth_headers(credentials)
            )

            if response.status_code == 404:
                return {"work_id": post_id, "status": "not_found"}
            elif response.status_code >= 400:
                return {"work_id": post_id, "status": "error", "error": response.text}

            work_data = response.json()

            # エピソード一覧取得
            eps_response = await client.get(
                f"{self.API_BASE}/works/{post_id}/episodes",
                headers=self._get_auth_headers(credentials),
            )
            episodes = (
                eps_response.json().get("episodes", []) if eps_response.status_code == 200 else []
            )

            return {
                "work_id": post_id,
                "title": work_data.get("title"),
                "status": work_data.get("status", "published"),
                "episode_count": len(episodes),
                "total_views": work_data.get("total_views", 0),
                "url": f"https://kakuyomu.jp/works/{post_id}",
            }

        except Exception as e:
            logger.warning(f"ステータス取得失敗: {e}")
            return {"work_id": post_id, "status": "unknown", "error": str(e)}

    def _map_genre(self, genre: str) -> str:
        """内部ジャンルをカクヨムジャンルコードにマッピング"""
        genre_map = {
            "fantasy": "fantasy",
            "sf": "sf",
            "horror": "horror",
            "mystery": "mystery",
            "romance": "romance",
            "general": "literary",
            "history": "history",
            "detective": "detective",
        }
        return genre_map.get(genre, "literary")

    def _format_for_kakuyomu(self, content: str) -> str:
        """カクヨム用フォーマット変換（Markdownベース）"""
        # カクヨムはMarkdown記法をサポート
        # 改行正規化
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        content = content.strip()

        # ルビ記法 |漢字《かんじ》| はそのまま対応
        # 画像プレースホルダはMarkdownのまま保持

        return content

    async def close(self):
        """リソース解放"""
        await self._close_client()


def create_kakuyomu_publisher(timeout: float = 30.0) -> KakuyomuPublisher:
    """ファクトリ関数"""
    return KakuyomuPublisher(timeout=timeout)
