"""
src/services/publishers/kindle.py - Amazon KDP Publisher

Amazon KDP API (OAuth2) を使用。
※ 利用にはKDP APIアクセス申請・承認が必要（法人向け）
APIドキュメント: https://developer-docs.amazon.com/kdp-api
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
class KindleCredentials(PublisherCredentials):
    """Amazon KDP 認証情報 (OAuth2 - LWA)"""

    client_id: str = ""  # LWA Client ID
    client_secret: str = ""  # LWA Client Secret
    refresh_token: str = ""  # LWA Refresh Token
    access_token: str = ""  # LWA Access Token
    token_expires_at: float = 0
    marketplace_id: str = "A1VC38T7YXB528"  # 日本: A1VC38T7YXB528

    def __post_init__(self):
        self.platform = "kindle"


class KindlePublisher(PublisherAdapter):
    """Amazon KDP 投稿アダプタ（公式OAuth2 API）"""

    platform = "kindle"
    description = "Amazon KDP（公式OAuth2 API）"

    rate_limit_per_minute: int = 30
    rate_limit_per_hour: int = 500

    # API エンドポイント
    API_BASE = "https://sellingpartnerapi-fe.amazon.com"
    AUTH_URL = "https://api.amazon.com/auth/o2/token"

    # KDP API スコープ
    SCOPE = "kdp:publish kdp:catalog"

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

    async def _ensure_valid_token(self, credentials: KindleCredentials) -> str:
        """LWAアクセストークン取得・リフレッシュ"""
        now = time.time()

        if credentials.access_token and credentials.token_expires_at > now + 60:
            return credentials.access_token

        if not credentials.refresh_token:
            raise AuthError(
                "リフレッシュトークンがありません。"
                "LWA認証フローで取得してください（https://developer-docs.amazon.com/kdp-api）",
                self.platform,
            )

        client = self._get_client()
        auth_header = base64.b64encode(
            f"{credentials.client_id}:{credentials.client_secret}".encode()
        ).decode()

        try:
            response = await client.post(
                self.AUTH_URL,
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": credentials.refresh_token,
                },
            )

            if response.status_code >= 400:
                raise AuthError(f"LWAトークンリフレッシュ失敗: {response.text}", self.platform)

            token_data = response.json()
            credentials.access_token = token_data["access_token"]
            credentials.token_expires_at = now + token_data.get("expires_in", 3600)

            logger.info("KDPトークンリフレッシュ完了")
            return credentials.access_token

        except AuthError:
            raise
        except httpx.RequestError as e:
            raise NetworkError(f"LWA接続エラー: {e}", self.platform)

    def _get_auth_headers(self, credentials: KindleCredentials) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {credentials.access_token}",
            "x-amz-access-token": credentials.access_token,
        }

    async def authenticate(self, credentials: KindleCredentials) -> bool:
        """LWA認証確認"""
        if not credentials.client_id or not credentials.client_secret:
            raise AuthError("Client ID と Client Secret が必要です", self.platform)

        if not credentials.refresh_token:
            raise AuthError(
                "Refresh Token が必要です。"
                "LWA認証フローで取得してください: "
                "https://developer-docs.amazon.com/kdp-api/docs/authentication",
                self.platform,
            )

        try:
            await self._ensure_valid_token(credentials)
            logger.info("KDP認証成功")
            return True

        except AuthError:
            raise
        except Exception as e:
            raise AuthError(f"認証中にエラーが発生しました: {e}", self.platform)

    @async_retry(max_attempts=3, base_delay=3.0)
    async def publish(
        self, novel: dict[str, Any], chapter: dict[str, Any], credentials: KindleCredentials
    ) -> PublishResult:
        """新規書籍作成（KDPでは書籍単位、コンテンツはEPUB/KPFアップロード）"""
        await self._ensure_valid_token(credentials)
        client = self._get_client()

        try:
            # 1. 書籍メタデータ登録
            book_payload = {
                "title": novel.get("title", "無題"),
                "description": novel.get("synopsis", ""),
                "language": "ja",
                "categories": self._map_categories(novel.get("genre", "general")),
                "keywords": novel.get("tags", [])[:7],  # KDPは最大7キーワード
                "contributors": [
                    {"role": "Author", "name": novel.get("author", "AI Novel Engine")}
                ],
                "publishing_rights": "world",
                "status": "draft",
            }

            response = await client.post(
                f"{self.API_BASE}/kdp/2023-11-01/books",
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
            book_id = book_data.get("bookId") or book_data.get("id")

            if not book_id:
                raise ValidationError("書籍IDが返却されませんでした", self.platform)

            # 2. コンテンツアップロード（EPUB生成が必要）
            # ここでは簡易版としてプレースホルダー
            # 実際にはEPUBファイルを生成し、presigned URLでS3アップロード
            _ = self._generate_epub_placeholder(novel, chapter)

            # コンテンツアップロード用のpresigned URL取得
            upload_response = await client.post(
                f"{self.API_BASE}/kdp/2023-11-01/books/{book_id}/content/upload-url",
                headers=self._get_auth_headers(credentials),
                json={"contentType": "application/epub+zip"},
            )

            if upload_response.status_code >= 400:
                raise ValidationError(
                    f"アップロードURL取得失敗: {upload_response.text}", self.platform
                )

            upload_data = upload_response.json()
            _ = upload_data.get("uploadUrl")

            # S3へ直接アップロード（簡易版：実装省略）
            # await self._upload_to_s3(upload_url, epub_content)

            return PublishResult(
                success=True,
                platform=self.platform,
                post_id=book_id,
                url=f"https://kdp.amazon.com/books/{book_id}",
                metadata={
                    "book_id": book_id,
                    "status": "draft",
                    "note": "EPUBアップロードは別途実装必要",
                },
            )

        except (ValidationError, RateLimitError):
            raise
        except httpx.RequestError as e:
            raise NetworkError(f"接続エラー: {e}", self.platform)
        except Exception as e:
            raise NetworkError(f"投稿中にエラーが発生しました: {e}", self.platform)

    @async_retry(max_attempts=3, base_delay=3.0)
    async def update_chapter(
        self, post_id: str, chapter: dict[str, Any], credentials: KindleCredentials
    ) -> PublishResult:
        """既存書籍のコンテンツ更新（KDPでは書籍全体の再アップロード）"""
        await self._ensure_valid_token(credentials)
        client = self._get_client()
        book_id = post_id

        try:
            # KDPではチャプター単位の追加はなく、書籍コンテンツ全体を置換
            # 既存チャプター取得して結合、新しいEPUB生成して再アップロード

            # 既存書籍情報取得
            response = await client.get(
                f"{self.API_BASE}/kdp/2023-11-01/books/{book_id}",
                headers=self._get_auth_headers(credentials),
            )

            if response.status_code == 404:
                raise ValidationError(f"書籍が見つかりません: {book_id}", self.platform)
            elif response.status_code >= 400:
                raise ValidationError(f"書籍情報取得失敗: {response.text}", self.platform)

            # 新しいコンテンツ生成・アップロード（実装省略：EPUB生成が必要）
            _ = self._generate_epub_placeholder({"title": ""}, chapter)

            upload_response = await client.post(
                f"{self.API_BASE}/kdp/2023-11-01/books/{book_id}/content/upload-url",
                headers=self._get_auth_headers(credentials),
                json={"contentType": "application/epub+zip"},
            )

            if upload_response.status_code >= 400:
                raise ValidationError(
                    f"アップロードURL取得失敗: {upload_response.text}", self.platform
                )

            return PublishResult(
                success=True,
                platform=self.platform,
                post_id=book_id,
                url=f"https://kdp.amazon.com/books/{book_id}",
                metadata={
                    "book_id": book_id,
                    "status": "updated",
                    "note": "書籍全体の再アップロードが必要",
                },
            )

        except (ValidationError, RateLimitError):
            raise
        except httpx.RequestError as e:
            raise NetworkError(f"接続エラー: {e}", self.platform)
        except Exception as e:
            raise NetworkError(f"更新中にエラーが発生しました: {e}", self.platform)

    async def get_post_status(self, post_id: str, credentials: KindleCredentials) -> dict[str, Any]:
        """書籍ステータス取得"""
        await self._ensure_valid_token(credentials)
        client = self._get_client()

        try:
            response = await client.get(
                f"{self.API_BASE}/kdp/2023-11-01/books/{post_id}",
                headers=self._get_auth_headers(credentials),
            )

            if response.status_code == 404:
                return {"book_id": post_id, "status": "not_found"}
            elif response.status_code >= 400:
                return {"book_id": post_id, "status": "error", "error": response.text}

            book_data = response.json()

            return {
                "book_id": post_id,
                "title": book_data.get("title"),
                "status": book_data.get("publishingStatus", "draft"),
                "url": f"https://kdp.amazon.com/books/{post_id}",
            }

        except Exception as e:
            return {"book_id": post_id, "status": "unknown", "error": str(e)}

    def _map_categories(self, genre: str) -> list[dict[str, str]]:
        """ジャンルをKDPカテゴリ（BISAC）にマッピング"""
        category_map = {
            "fantasy": [{"categoryId": "FIC009000", "name": "Fantasy"}],
            "sf": [{"categoryId": "FIC028000", "name": "Science Fiction"}],
            "horror": [{"categoryId": "FIC015000", "name": "Horror"}],
            "mystery": [{"categoryId": "FIC022000", "name": "Mystery & Detective"}],
            "romance": [{"categoryId": "FIC027000", "name": "Romance"}],
            "general": [{"categoryId": "FIC000000", "name": "General"}],
            "history": [{"categoryId": "FIC016000", "name": "Historical"}],
        }
        return category_map.get(genre, [{"categoryId": "FIC000000", "name": "General"}])

    def _generate_epub_placeholder(self, novel: dict, chapter: dict) -> bytes:
        """EPUBプレースホルダー生成（実装時は適切なEPUBライブラリ使用）"""
        # 実際の実装では ebooklib 等を使用してEPUB生成
        title = novel.get("title") or chapter.get("title", "無題")
        _ = chapter.get("content", "")
        post_id = novel.get("id", "unknown")

        # 簡易EPUB構造（実用には不十分）
        epub_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>{title}</dc:title>
        <dc:language>ja</dc:language>
        <dc:identifier id="bookid">{post_id}</dc:identifier>
    </metadata>
    <manifest>
        <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
        <item id="ch1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    </manifest>
    <spine>
        <itemref idref="nav"/>
        <itemref idref="ch1"/>
    </spine>
</package>"""

        return epub_content.encode("utf-8")

    async def close(self):
        await self._close_client()


def create_kindle_publisher(timeout: float = 30.0) -> KindlePublisher:
    return KindlePublisher(timeout=timeout)
