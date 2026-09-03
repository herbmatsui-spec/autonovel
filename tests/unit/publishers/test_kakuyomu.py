"""
tests/unit/publishers/test_kakuyomu.py - カクヨムPublisherテスト
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from src.services.publishers.kakuyomu import KakuyomuPublisher, KakuyomuCredentials
from src.services.publishers.base import PublishResult, AuthError, RateLimitError, ValidationError, NetworkError


class TestKakuyomuPublisher:
    """KakuyomuPublisherテスト"""
    
    @pytest.fixture
    def publisher(self):
        return KakuyomuPublisher(timeout=10.0)
    
    @pytest.fixture
    def credentials(self):
        return KakuyomuCredentials(api_token="test_token_123", user_id="user_456")
    
    def test_publisher_initialization(self, publisher):
        """初期化テスト"""
        assert publisher.platform == "kakuyomu"
        assert publisher.description == "カクヨム（非公式REST API）"
        assert publisher.rate_limit_per_minute == 30
        assert publisher.rate_limit_per_hour == 500
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, publisher, credentials):
        """認証成功テスト"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "user_456", "name": "Test User"}
        
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.get = AsyncMock(return_value=mock_response)
        
        publisher._client = mock_client
        
        result = await publisher.authenticate(credentials)
        
        assert result is True
        assert credentials.user_id == "user_456"
        mock_client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_invalid_token(self, publisher, credentials):
        """無効トークンテスト"""
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        mock_client = AsyncMock()
        mock_client.is_closed = False
        mock_client.get = AsyncMock(return_value=mock_response)
        publisher._client = mock_client
        
        with pytest.raises(AuthError) as exc_info:
            await publisher.authenticate(credentials)
        
        assert "無効または期限切れ" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_authenticate_missing_token(self, publisher):
        """トークンなしテスト"""
        creds = KakuyomuCredentials()  # api_tokenなし
        
        with pytest.raises(AuthError) as exc_info:
            await publisher.authenticate(creds)
        
        assert "APIトークンが必要です" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_publish_success(self, publisher, credentials):
        """投稿成功テスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        # 作品作成レスポンス
        work_response = MagicMock()
        work_response.status_code = 201
        work_response.json.return_value = {"id": "work_123", "title": "テスト小説"}
        
        # エピソード投稿レスポンス
        episode_response = MagicMock()
        episode_response.status_code = 201
        episode_response.json.return_value = {"id": "episode_456", "number": 1}
        
        mock_client.post = AsyncMock(side_effect=[work_response, episode_response])
        
        novel = {"title": "テスト小説", "synopsis": "あらすじ", "genre": "fantasy", "tags": ["ファンタジー"]}
        chapter = {"ep_num": 1, "title": "第1話", "content": "本文テスト"}
        
        result = await publisher.publish(novel, chapter, credentials)
        
        assert result.success is True
        assert result.platform == "kakuyomu"
        assert result.post_id == "work_123"
        assert result.metadata["work_id"] == "work_123"
        assert result.metadata["episode_id"] == "episode_456"
        assert mock_client.post.call_count == 2
    
    @pytest.mark.asyncio
    async def test_publish_rate_limit(self, publisher, credentials):
        """レート制限テスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "30"}
        
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(RateLimitError) as exc_info:
            await publisher.publish({"title": "Test"}, {"ep_num": 1}, credentials)
        
        assert exc_info.value.retry_after == 30.0
    
    @pytest.mark.asyncio
    async def test_publish_validation_error(self, publisher, credentials):
        """バリデーションエラーテスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Title too long"}
        
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(ValidationError) as exc_info:
            await publisher.publish({"title": "Test"}, {"ep_num": 1}, credentials)
        
        assert "Title too long" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_chapter(self, publisher, credentials):
        """話追加テスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "episode_789", "number": 2}
        
        publisher._client.post = AsyncMock(return_value=mock_response)
        
        chapter = {"ep_num": 2, "title": "第2話", "content": "第2話本文"}
        
        result = await publisher.update_chapter("work_123", chapter, credentials)
        
        assert result.success is True
        assert result.post_id == "work_123"
        assert result.metadata["episode_number"] == 2
    
    @pytest.mark.asyncio
    async def test_update_chapter_not_found(self, publisher, credentials):
        """作品未発見テスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        mock_client.post = AsyncMock(return_value=mock_response)
        
        with pytest.raises(ValidationError) as exc_info:
            await publisher.update_chapter("nonexistent", {"ep_num": 2}, credentials)
        
        assert "見つかりません" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_post_status(self, publisher, credentials):
        """ステータス取得テスト"""
        mock_client = AsyncMock()
        mock_client.is_closed = False
        publisher._client = mock_client
        
        work_response = MagicMock()
        work_response.status_code = 200
        work_response.json.return_value = {
            "id": "work_123",
            "title": "テスト小説",
            "status": "published",
            "total_views": 1000,
        }
        
        eps_response = MagicMock()
        eps_response.status_code = 200
        eps_response.json.return_value = {
            "episodes": [{"id": "ep1"}, {"id": "ep2"}, {"id": "ep3"}]
        }
        
        publisher._client.get = AsyncMock(side_effect=[work_response, eps_response])
        
        status = await publisher.get_post_status("work_123", credentials)
        
        assert status["work_id"] == "work_123"
        assert status["title"] == "テスト小説"
        assert status["status"] == "published"
        assert status["episode_count"] == 3
        assert status["total_views"] == 1000
    
    def test_format_for_kakuyomu(self, publisher):
        """カクヨム用フォーマットテスト"""
        content = "第1行\n\n第2行\n\n\n第3行"
        formatted = publisher._format_for_kakuyomu(content)
        
        # Markdownとして有効な形で返る
        assert "第1行" in formatted
        assert "第2行" in formatted
        assert "第3行" in formatted
    
    def test_map_genre(self, publisher):
        """ジャンルマッピングテスト"""
        assert publisher._map_genre("fantasy") == "fantasy"
        assert publisher._map_genre("sf") == "sf"
        assert publisher._map_genre("general") == "literary"
        assert publisher._map_genre("unknown") == "literary"  # デフォルト


if __name__ == "__main__":
    pytest.main([__file__, "-v"])