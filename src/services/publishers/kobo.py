"""
src/services/publishers/kobo.py - 楽天Kobo Writing Life Publisher

公式API (OAuth2) を使用。
APIドキュメント: https://writinglife.kobo.com/developer
※ 利用には審査・承認が必要
"""

from __future__ import annotations

import asyncio
import base64
import logging
import time
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
class KoboCredentials(PublisherCredentials):
    """Kobo Writing Life 認証情報 (OAuth2)"""

    client_id: str = ""
    client_secret: str = ""
    access_token: str = ""
    refresh_token: str = ""
    token_expires_at: float = 0
    publisher_id: str = ""  # Kobo上の出版社ID

    def __post_init__(self):
        self.platform = "kobo"


class KoboPublisher(PublisherAdapter):
    """楽天Kobo Writing Life 投稿アダプタ（公式OAuth2 API）"""

    platform = "kobo"
    description = "楽天Kobo Writing Life（公式OAuth2 API）"

    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000

    # API エンドポイント
    API_BASE = "https://api.kobowritinglife.com/v1"
    AUTH_URL = "https://auth.kobowritinglife.com/oauth/token"

    def __init__(self, timeout: float = 30.0):
        super().__init__()
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "User-Agent": "AutoNovel/1.0",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def _close_client(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _ensure_valid_token(self, credentials: KoboCredentials) -> str:
        """アクセストークンが有効か確認、期限切れならリフレッシュ"""
        now = time.time()

        if credentials.access_token and credentials.token_expires_at > now + 60:
            return credentials.access_token

        if not credentials.refresh_token:
            raise AuthError("リフレッシュトークンがありません。初回認証が必要です", self.platform)

        # トークンリフレッシュ
        client = self._get_client()
        auth_header = base64.b64encode(
            f"{credentials.client_id}:{credentials.client_secret}".encode()
        ).decode()

        response = await client.post(
            self.AUTH_URL,
            headers={"Authorization": f"Basic {auth_header}"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": credentials.refresh_token,
            },
        )

        if response.status_code >= 400:
            raise AuthError(f"トークンリフレッシュ失敗: {response.text}", self.platform)

        token_data = response.json()
        credentials.access_token = token_data["access_token"]
        credentials.refresh_token = token_data.get("refresh_token", credentials.refresh_token)
        credentials.token_expires_at = now + token_data.get("expires_in", 3600)

        logger.info("Koboトークンリフレッシュ完了")
        return credentials.access_token

    def _get_auth_headers(self, credentials: KoboCredentials) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {credentials.access_token}",
        }

    async def authenticate(self, credentials: KoboCredentials) -> bool:
        """OAuth2 クライアントクレデンシャルフローで初回トークン取得"""
        if not credentials.client_id or not credentials.client_secret:
            raise AuthError("Client ID と Client Secret が必要です", self.platform)

        # 既存トークンがある場合は検証のみ
        if credentials.access_token:
            try:
                await self._ensure_valid_token(credentials)
                # 出版社ID取得
                await self._fetch_publisher_id(credentials)
                return True
            except AuthError:
                pass  # トークン無効の場合は以下で再取得

        # 初回トークン取得（Client Credentials Grant）
        client = self._get_client()
        auth_header = base64.b64encode(
            f"{credentials.client_id}:{credentials.client_secret}".encode()
        ).decode()

        try:
            response = await client.post(
                self.AUTH_URL,
                headers={"Authorization": f"Basic {auth_header}"},
                data={"grant_type": "client_credentials"},
            )

            if response.status_code >= 400:
                raise AuthError(f"認証失敗: {response.text}", self.platform)

            token_data = response.json()
            credentials.access_token = token_data["access_token"]
            credentials.refresh_token = token_data.get("refresh_token", "")
            credentials.token_expires_at = time.time() + token_data.get("expires_in", 3600)

            # 出版社ID取得
            await self._fetch_publisher_id(credentials)

            logger.info("Kobo認証成功", extra={"publisher_id": credentials.publisher_id})
            return True

        except AuthError:
            raise
        except httpx.RequestError as e:
            raise NetworkError(f"接続エラー: {e}", self.platform)
        except Exception as e:
            raise AuthError(f"認証中にエラーが発生しました: {e}", self.platform)

    async def _fetch_publisher_id(self, credentials: KoboCredentials):
        """出版社IDを取得"""
        client = self._get_client()
        response = await client.get(
            f"{self.API_BASE}/publishers", headers=self._get_auth_headers(credentials)
        )

        if response.status_code == 200:
            publishers = response.json().get("publishers", [])
            if publishers:
                credentials.publisher_id = publishers[0].get("id", "")

    @async_retry(max_attempts=3, base_delay=2.0)
    async def publish(
        self, novel: dict[str, Any], chapter: dict[str, Any], credentials: KoboCredentials
    ) -> PublishResult:
        """新規書籍作成（Koboでは書籍単位で管理、チャプターは後から追加）"""
        await self._ensure_valid_token(credentials)
        client = self._get_client()

        try:
            # 1. 書籍作成
            book_payload = {
                "title": novel.get("title", "無題"),
                "description": novel.get("synopsis", ""),
                "language": "ja",
                "categories": self._map_categories(novel.get("genre", "general")),
                "keywords": novel.get("tags", []),
                "publisher_id": credentials.publisher_id,
                "rights": "world",
                "status": "draft",  # まず下書きで作成
            }

            response = await client.post(
                f"{self.API_BASE}/books",
                headers=self._get_auth_headers(credentials),
                json=book_payload,
            )

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    "レート制限に達しました", self.platform, retry_after=retry_after
                )
            elif response.status_code >= 400:
                raise ValidationError(f"書籍作成失敗: {response.text}", self.platform)

            book_data = response.json()
            book_id = book_data.get("id")

            if not book_id:
                raise ValidationError("書籍IDが返却されませんでした", self.platform)

            # 2. 第1章アップロード（EPUB生成またはHTML直接）
            # 簡易版: HTMLチャプターとしてアップロード
            chapter_html = self._build_chapter_html(novel, chapter)

            chapter_payload = {
                "book_id": book_id,
                "title": chapter.get("title", "第1章"),
                "content": chapter_html,
                "order": 1,
            }

            response = await client.post(
                f"{self.API_BASE}/books/{book_id}/chapters",
                headers=self._get_auth_headers(credentials),
                json=chapter_payload,
            )

            if response.status_code >= 400:
                raise ValidationError(f"チャプター追加失敗: {response.text}", self.platform)

            chapter_data = response.json()
            chapter_id = chapter_data.get("id")

            return PublishResult(
                success=True,
                platform=self.platform,
                post_id=book_id,
                url=f"https://writinglife.kobo.com/publisher/{credentials.publisher_id}/books/{book_id}",
                metadata={"book_id": book_id, "chapter_id": chapter_id, "chapter_number": 1},
            )

        except (ValidationError, RateLimitError):
            raise
        except httpx.RequestError as e:
            raise NetworkError(f"接続エラー: {e}", self.platform)
        except Exception as e:
            raise NetworkError(f"投稿中にエラーが発生しました: {e}", self.platform)

    @async_retry(max_attempts=3, base_delay=2.0)
    async def update_chapter(
        self, post_id: str, chapter: dict[str, Any], credentials: KoboCredentials
    ) -> PublishResult:
        """既存書籍にチャプター追加"""
        await self._ensure_valid_token(credentials)
        client = self._get_client()
        book_id = post_id

        try:
            # 既存チャプター数取得して次順序決定
            response = await client.get(
                f"{self.API_BASE}/books/{book_id}/chapters",
                headers=self._get_auth_headers(credentials),
            )

            chapters = response.json().get("chapters", []) if response.status_code == 200 else []
            next_order = len(chapters) + 1

            chapter_html = self._build_chapter_html({"title": ""}, chapter)

            chapter_payload = {
                "book_id": book_id,
                "title": chapter.get("title", f"第{next_order}章"),
                "content": chapter_html,
                "order": next_order,
            }

            response = await client.post(
                f"{self.API_BASE}/books/{book_id}/chapters",
                headers=self._get_auth_headers(credentials),
                json=chapter_payload,
            )

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", 60))
                raise RateLimitError(
                    "レート制限に達しました", self.platform, retry_after=retry_after
                )
            elif response.status_code >= 400:
                raise ValidationError(f"チャプター追加失敗: {response.text}", self.platform)

            chapter_data = response.json()
            chapter_id = chapter_data.get("id")

            return PublishResult(
                success=True,
                platform=self.platform,
                post_id=book_id,
                url=f"https://writinglife.kobo.com/publisher/{credentials.publisher_id}/books/{book_id}",
                metadata={
                    "book_id": book_id,
                    "chapter_id": chapter_id,
                    "chapter_number": next_order,
                },
            )

        except (ValidationError, RateLimitError):
            raise
        except httpx.RequestError as e:
            raise NetworkError(f"接続エラー: {e}", self.platform)
        except Exception as e:
            raise NetworkError(f"チャプター追加中にエラーが発生しました: {e}", self.platform)

    async def get_post_status(self, post_id: str, credentials: KoboCredentials) -> dict[str, Any]:
        """書籍ステータス取得"""
        await self._ensure_valid_token(credentials)
        client = self._get_client()

        try:
            response = await client.get(
                f"{self.API_BASE}/books/{post_id}", headers=self._get_auth_headers(credentials)
            )

            if response.status_code == 404:
                return {"book_id": post_id, "status": "not_found"}
            elif response.status_code >= 400:
                return {"book_id": post_id, "status": "error", "error": response.text}

            book_data = response.json()

            return {
                "book_id": post_id,
                "title": book_data.get("title"),
                "status": book_data.get("status", "draft"),
                "chapter_count": book_data.get("chapter_count", 0),
                "url": f"https://writinglife.kobo.com/publisher/{credentials.publisher_id}/books/{post_id}",
            }

        except Exception as e:
            return {"book_id": post_id, "status": "unknown", "error": str(e)}

    def _map_categories(self, genre: str) -> list[str]:
        """ジャンルをKoboカテゴリにマッピング（BISACコード）"""
        category_map = {
            "fantasy": ["FIC009000"],  # FICTION / Fantasy / General
            "sf": ["FIC028000"],  # FICTION / Science Fiction / General
            "horror": ["FIC015000"],  # FICTION / Horror / General
            "mystery": ["FIC022000"],  # FICTION / Mystery & Detective / General
            "romance": ["FIC027000"],  # FICTION / Romance / General
            "general": ["FIC000000"],  # FICTION / General
            "history": ["FIC016000"],  # FICTION / Historical / General
        }
        return category_map.get(genre, ["FIC000000"])

    def _build_chapter_html(self, novel: dict[str, Any], chapter: dict[str, Any]) -> str:
        """チャプターHTML生成"""
        title = chapter.get("title", "無題")
        content = chapter.get("content", "")

        # 改行を<p>タグに変換
        paragraphs = content.split("\n\n")
        html_paragraphs = [f"<p>{p.strip()}</p>" for p in paragraphs if p.strip()]

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title}</title>
</head>
<body>
    <h1>{title}</h1>
    {"".join(html_paragraphs)}
</body>
</html>"""

    async def close(self):
        await self._close_client()


def create_kobo_publisher(timeout: float = 30.0) -> KoboPublisher:
    return KoboPublisher(timeout=timeout)
