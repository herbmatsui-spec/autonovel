"""
tests/unit/publishers/test_kobo.py - Kobo Publisherテスト
"""

from __future__ import annotations

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.services.publishers.kobo import KoboPublisher, KoboCredentials
from src.services.publishers.base import PublishResult, AuthError, RateLimitError, ValidationError, NetworkError


class TestKoboPublisher:
    """KoboPublisherテスト"""
    
    @pytest.fixture
    def publisher(self):
        return KoboPublisher(timeout=10.0)
    
    @pytest.fixture
    def credentials(self):
        return KoboCredentials(
            client_id="test_client",
            client_secret="test_secret",
            access_token="valid_token",
            token_expires_at=time.time() + 3600,
            publisher_id="pub_123"
        )
    
    def test_publisher_initialization(self, publisher):
        """初期化テスト"""
        assert publisher.platform == "kobo"
        assert publisher.description == "楽天Kobo Writing Life（公式OAuth2 API）"
        assert publisher.rate_limit_per_minute == 60
    
    @pytest.mark.asyncio
    async def test_ensure_valid_token_cached(self, publisher, credentials):
        """キャッシュトークン使用テスト"""
        token = await publisher._ensure_valid_token(credentials)
        assert token == "valid_token"
    
    @pytest.mark.asyncio
    async def test_ensure_valid_token_refresh(self, publisher):
        """トークンリフレッシュテスト"""
        creds = KoboCredentials(
            client_id="test_client",
            client_secret="test_secret",
            refresh_token="refresh_123",
            token_expires_at=time.time() - 100,  # 期限切れ
        )
        
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
        }
        
        mock_client.post = AsyncMock(return_value=mock_response)
        
        token = await publisher._ensure_valid_token(creds)
        
        assert token == "new_token"
        assert creds.access_token == "new_token"
        assert creds.refresh_token == "new_refresh"
        assert creds.token_expires_at > time.time()
    
    @pytest.mark.asyncio
    async def test_authenticate_with_existing_token(self, publisher, credentials):
        """既存トークンで認証テスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        # _ensure_valid_tokenでトークン確認
        # _fetch_publisher_idで出版社ID取得
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"publishers": [{"id": "pub_123"}]}
        
        publisher._client.get = AsyncMock(return_value=mock_response)
        
        result = await publisher.authenticate(credentials)
        
        assert result is True
        assert credentials.publisher_id == "pub_123"
    
    @pytest.mark.asyncio
    async def test_authenticate_new_token(self, publisher):
        """新規トークン取得テスト"""
        creds = KoboCredentials(client_id="test_client", client_secret="test_secret")
        
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        # トークン取得
        token_response = MagicMock()
        token_response.status_code = 200
        token_response.json.return_value = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires_in": 3600,
        }
        
        # 出版社ID取得
        pub_response = MagicMock()
        pub_response.status_code = 200
        pub_response.json.return_value = {"publishers": [{"id": "pub_456"}]}
        
        mock_client.post = AsyncMock(return_value=token_response)
        mock_client.get = AsyncMock(return_value=pub_response)
        
        result = await publisher.authenticate(creds)
        
        assert result is True
        assert creds.access_token == "new_token"
        assert creds.publisher_id == "pub_456"
    
    @pytest.mark.asyncio
    async def test_publish_success(self, publisher, credentials):
        """書籍作成・チャプター追加成功テスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        # 書籍作成
        book_response = MagicMock()
        book_response.status_code = 201
        book_response.json.return_value = {"id": "book_789"}
        
        # チャプター追加
        chapter_response = MagicMock()
        chapter_response.status_code = 201
        chapter_response.json.return_value = {"id": "chapter_101"}
        
        mock_client.post = AsyncMock(side_effect=[book_response, chapter_response])
        
        novel = {"title": "テスト書籍", "synopsis": "あらすじ", "genre": "fantasy", "tags": ["ファンタジー"]}
        chapter = {"ep_num": 1, "title": "第1章", "content": "本文テスト"}
        
        result = await publisher.publish(novel, chapter, credentials)
        
        assert result.success is True
        assert result.platform == "kobo"
        assert result.post_id == "book_789"
        assert result.metadata["book_id"] == "book_789"
        assert result.metadata["chapter_id"] == "chapter_101"
    
    @pytest.mark.asyncio
    async def test_update_chapter(self, publisher, credentials):
        """チャプター追加テスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        # 既存チャプター取得
        chapters_response = MagicMock()
        chapters_response.status_code = 200
        chapters_response.json.return_value = {"chapters": [{"id": "ch1"}, {"id": "ch2"}]}
        
        # 新規チャプター追加
        chapter_response = MagicMock()
        chapter_response.status_code = 201
        chapter_response.json.return_value = {"id": "chapter_103"}
        
        publisher._client.get = AsyncMock(return_value=chapters_response)
        publisher._client.post = AsyncMock(return_value=chapter_response)
        
        chapter = {"ep_num": 3, "title": "第3章", "content": "第3章本文"}
        
        result = await publisher.update_chapter("book_789", chapter, credentials)
        
        assert result.success is True
        assert result.metadata["chapter_number"] == 3
    
    @pytest.mark.asyncio
    async def test_get_post_status(self, publisher, credentials):
        """ステータス取得テスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "book_789",
            "title": "テスト書籍",
            "status": "published",
            "chapter_count": 5,
        }
        
        mock_client.get = AsyncMock(return_value=mock_response)
        
        status = await publisher.get_post_status("book_789", credentials)
        
        assert status["book_id"] == "book_789"
        assert status["title"] == "テスト書籍"
        assert status["status"] == "published"
        assert status["chapter_count"] == 5
    
    def test_map_categories(self, publisher):
        """カテゴリマッピングテスト"""
        cats = publisher._map_categories("fantasy")
        assert "FIC009000" in cats
        
        cats = publisher._map_categories("general")
        assert "FIC000000" in cats
    
    def test_build_chapter_html(self, publisher):
        """チャプターHTML生成テスト"""
        novel = {"title": "テスト書籍"}
        chapter = {"title": "第1章", "content": "第1段落\n\n第2段落"}
        
        html = publisher._build_chapter_html(novel, chapter)
        
        assert "第1章" in html
        assert "<p>第1段落</p>" in html
        assert "<p>第2段落</p>" in html
        assert "xmlns=" in html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])