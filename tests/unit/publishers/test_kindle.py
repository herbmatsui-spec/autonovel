"""
tests/unit/publishers/test_kindle.py - Kindle Publisherテスト
"""

from __future__ import annotations

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.services.publishers.kindle import KindlePublisher, KindleCredentials
from src.services.publishers.base import PublishResult, AuthError, RateLimitError, ValidationError, NetworkError


class TestKindlePublisher:
    """KindlePublisherテスト"""
    
    @pytest.fixture
    def publisher(self):
        return KindlePublisher(timeout=10.0)
    
    @pytest.fixture
    def credentials(self):
        return KindleCredentials(
            client_id="test_client",
            client_secret="test_secret",
            refresh_token="refresh_123",
            access_token="valid_token",
            token_expires_at=time.time() + 3600,
        )
    
    def test_publisher_initialization(self, publisher):
        """初期化テスト"""
        assert publisher.platform == "kindle"
        assert publisher.description == "Amazon KDP（公式OAuth2 API）"
        assert publisher.rate_limit_per_minute == 30
    
    @pytest.mark.asyncio
    async def test_ensure_valid_token_cached(self, publisher, credentials):
        """キャッシュトークン使用テスト"""
        token = await publisher._ensure_valid_token(credentials)
        assert token == "valid_token"
    
    @pytest.mark.asyncio
    async def test_ensure_valid_token_refresh(self, publisher):
        """トークンリフレッシュテスト"""
        creds = KindleCredentials(
            client_id="test_client",
            client_secret="test_secret",
            refresh_token="refresh_123",
            token_expires_at=time.time() - 100,
        )
        
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "expires_in": 3600,
        }
        
        mock_client.post = AsyncMock(return_value=mock_response)
        
        token = await publisher._ensure_valid_token(creds)
        
        assert token == "new_token"
        assert creds.access_token == "new_token"
        assert creds.token_expires_at > time.time()
    
    @pytest.mark.asyncio
    async def test_authenticate_missing_refresh_token(self, publisher):
        """リフレッシュトークンなしテスト"""
        creds = KindleCredentials(client_id="test_client", client_secret="test_secret")
        
        with pytest.raises(AuthError) as exc_info:
            await publisher.authenticate(creds)
        
        assert "Refresh Token" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_publish_success(self, publisher, credentials):
        """書籍作成成功テスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        # 書籍作成
        book_response = MagicMock()
        book_response.status_code = 201
        book_response.json.return_value = {"bookId": "book_999"}
        
        # アップロードURL取得
        upload_response = MagicMock()
        upload_response.status_code = 200
        upload_response.json.return_value = {"uploadUrl": "https://s3.amazonaws.com/upload/..."}
        
        mock_client.post = AsyncMock(side_effect=[book_response, upload_response])
        
        novel = {"title": "テスト本", "synopsis": "あらすじ", "genre": "fantasy", "tags": ["ファンタジー"], "author": "著者名"}
        chapter = {"ep_num": 1, "title": "第1章", "content": "本文テスト"}
        
        result = await publisher.publish(novel, chapter, credentials)
        
        assert result.success is True
        assert result.platform == "kindle"
        assert result.post_id == "book_999"
        assert result.metadata["book_id"] == "book_999"
        assert "EPUBアップロード" in result.metadata["note"]
    
    @pytest.mark.asyncio
    async def test_update_chapter(self, publisher, credentials):
        """コンテンツ更新テスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        # 既存書籍取得
        book_response = MagicMock()
        book_response.status_code = 200
        book_response.json.return_value = {"bookId": "book_999", "title": "テスト本"}
        
        # アップロードURL取得
        upload_response = MagicMock()
        upload_response.status_code = 200
        upload_response.json.return_value = {"uploadUrl": "https://s3.amazonaws.com/upload/..."}
        
        mock_client.get = AsyncMock(return_value=book_response)
        mock_client.post = AsyncMock(return_value=upload_response)
        
        chapter = {"ep_num": 2, "title": "第2章", "content": "第2章本文"}
        
        result = await publisher.update_chapter("book_999", chapter, credentials)
        
        assert result.success is True
        assert result.metadata["book_id"] == "book_999"
        assert "書籍全体の再アップロード" in result.metadata["note"]
    
    @pytest.mark.asyncio
    async def test_update_chapter_not_found(self, publisher, credentials):
        """書籍未発見テスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        book_response = MagicMock()
        book_response.status_code = 404
        
        mock_client.get = AsyncMock(return_value=book_response)
        
        with pytest.raises(ValidationError) as exc_info:
            await publisher.update_chapter("nonexistent", {"ep_num": 2}, credentials)
        
        assert "見つかりません" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_post_status(self, publisher, credentials):
        """ステータス取得テスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bookId": "book_999",
            "title": "テスト本",
            "publishingStatus": "published",
        }
        
        mock_client.get = AsyncMock(return_value=mock_response)
        
        status = await publisher.get_post_status("book_999", credentials)
        
        assert status["book_id"] == "book_999"
        assert status["title"] == "テスト本"
        assert status["status"] == "published"
    
    def test_map_categories(self, publisher):
        """カテゴリマッピングテスト"""
        cats = publisher._map_categories("fantasy")
        assert cats[0]["categoryId"] == "FIC009000"
        
        cats = publisher._map_categories("general")
        assert cats[0]["categoryId"] == "FIC000000"
    
    def test_generate_epub_placeholder(self, publisher):
        """EPUBプレースホルダー生成テスト"""
        # post_idが必要だが、このメソッドは引数で受け取る想定
        # 実装ではpublish/updateで生成される
        novel = {"title": "テスト"}
        chapter = {"title": "第1章", "content": "本文"}
        
        epub = publisher._generate_epub_placeholder(novel, chapter)
        
        assert b"package" in epub
        assert b"metadata" in epub
        assert b"dc:title" in epub


if __name__ == "__main__":
    pytest.main([__file__, "-v"])