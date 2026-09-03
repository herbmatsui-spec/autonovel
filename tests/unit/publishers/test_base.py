"""
tests/unit/publishers/test_base.py - Publisher基底クラスのテスト
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestPublisherDataClasses:
    """データクラスのテスト"""
    
    def test_publish_result_creation(self):
        """PublishResult作成テスト"""
        result = PublishResult(
            success=True,
            platform="narou",
            post_id="12345",
            url="https://example.com/12345",
            metadata={"episode": 1}
        )
        assert result.success is True
        assert result.platform == "narou"
        assert result.post_id == "12345"
        assert result.metadata["episode"] == 1
    
    def test_publish_result_defaults(self):
        """PublishResultデフォルト値テスト"""
        result = PublishResult(success=False, platform="kakuyomu")
        assert result.success is False
        assert result.platform == "kakuyomu"
        assert result.post_id is None
        assert result.url is None
        assert result.error is None
        assert result.metadata == {}
    
    def test_publisher_credentials_base(self):
        """PublisherCredentials基底クラステスト"""
        creds = PublisherCredentials(platform="test", extra={"custom": "value"})
        assert creds.platform == "test"
        assert creds.extra == {"custom": "value"}
    
    def test_narou_credentials(self):
        """NarouCredentialsテスト"""
        from src.services.publishers.narou import NarouCredentials
        creds = NarouCredentials(email="test@test.com", password="pass123")
        assert creds.email == "test@test.com"
        assert creds.password == "pass123"
        assert creds.platform == "narou"
    
    def test_kakuyomu_credentials(self):
        """KakuyomuCredentialsテスト"""
        from src.services.publishers.kakuyomu import KakuyomuCredentials
        creds = KakuyomuCredentials(api_token="token123", user_id="user456")
        assert creds.api_token == "token123"
        assert creds.user_id == "user456"
        assert creds.platform == "kakuyomu"
    
    def test_kobo_credentials(self):
        """KoboCredentialsテスト"""
        from src.services.publishers.kobo import KoboCredentials
        creds = KoboCredentials(client_id="id", client_secret="secret")
        assert creds.client_id == "id"
        assert creds.client_secret == "secret"
        assert creds.platform == "kobo"
    
    def test_kindle_credentials(self):
        """KindleCredentialsテスト"""
        from src.services.publishers.kindle import KindleCredentials
        creds = KindleCredentials(client_id="id", client_secret="secret", refresh_token="refresh")
        assert creds.client_id == "id"
        assert creds.client_secret == "secret"
        assert creds.refresh_token == "refresh"
        assert creds.platform == "kindle"


class TestPublisherExceptions:
    """例外クラステスト"""
    
    def test_publisher_error(self):
        """PublisherError基底テスト"""
        exc = PublisherError("test error", "narou", recoverable=True)
        assert str(exc) == "test error"
        assert exc.platform == "narou"
        assert exc.recoverable is True
    
    def test_auth_error(self):
        """AuthErrorテスト"""
        exc = AuthError("invalid credentials", "kakuyomu")
        assert exc.recoverable is False
        assert exc.platform == "kakuyomu"
    
    def test_rate_limit_error(self):
        """RateLimitErrorテスト"""
        exc = RateLimitError("rate limited", "kobo", retry_after=60.0)
        assert exc.recoverable is True
        assert exc.retry_after == 60.0
    
    def test_validation_error(self):
        """ValidationErrorテスト"""
        exc = ValidationError("invalid input", "kindle")
        assert exc.recoverable is False
    
    def test_network_error(self):
        """NetworkErrorテスト"""
        exc = NetworkError("connection failed", "narou")
        assert exc.recoverable is True


class TestAsyncRetry:
    """async_retryデコレータテスト"""
    
    @pytest.mark.asyncio
    async def test_retry_success_on_first_attempt(self):
        """初回成功テスト"""
        call_count = 0
        
        @async_retry(max_attempts=3, base_delay=0.01)
        async def succeed():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await succeed()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_success_after_failures(self):
        """リトライ後成功テスト"""
        call_count = 0
        
        @async_retry(max_attempts=3, base_delay=0.01)
        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("network error", "test")
            return "success"
        
        result = await fail_twice()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """リトライ尽きて失敗テスト"""
        call_count = 0
        
        @async_retry(max_attempts=3, base_delay=0.01)
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise NetworkError("network error", "test")
        
        with pytest.raises(NetworkError):
            await always_fail()
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """リトライ対象外例外は即失敗"""
        call_count = 0
        
        @async_retry(max_attempts=3, base_delay=0.01, retryable_exceptions=(NetworkError,))
        async def auth_fail():
            nonlocal call_count
            call_count += 1
            raise AuthError("auth failed", "test")
        
        with pytest.raises(AuthError):
            await auth_fail()
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_rate_limit_uses_retry_after(self):
        """RateLimitErrorのretry_afterを優先使用"""
        call_count = 0
        delays = []
        
        @async_retry(max_attempts=2, base_delay=10.0, retryable_exceptions=(RateLimitError,))
        async def rate_limited():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("rate limited", "test", retry_after=0.01)
            return "success"
        
        # sleepをモックして実行時間を測定
        with patch("asyncio.sleep") as mock_sleep:
            mock_sleep.side_effect = lambda d: delays.append(d)
            result = await rate_limited()
        
        assert result == "success"
        # retry_after(0.01) + jitter が使用される
        assert len(delays) == 1
        assert 0.01 <= delays[0] < 0.5  # retry_after + jitter程度


class MockPublisher(PublisherAdapter):
    """テスト用モックPublisher"""
    platform = "mock"
    description = "Mock Publisher"
    
    def __init__(self):
        super().__init__()
        self.auth_called = False
        self.publish_called = False
        self.update_called = False
        self.status_called = False
    
    async def authenticate(self, credentials: PublisherCredentials) -> bool:
        self.auth_called = True
        return True
    
    async def publish(self, novel, chapter, credentials):
        self.publish_called = True
        return PublishResult(success=True, platform=self.platform, post_id="123")
    
    async def update_chapter(self, post_id, chapter, credentials):
        self.update_called = True
        return PublishResult(success=True, platform=self.platform, post_id=post_id)
    
    async def get_post_status(self, post_id, credentials):
        self.status_called = True
        return {"post_id": post_id, "status": "published"}


class TestPublisherAdapterInterface:
    """PublisherAdapterインターフェーステスト"""
    
    @pytest.mark.asyncio
    async def test_mock_publisher_flow(self):
        """モックPublisherの一連の流れテスト"""
        publisher = MockPublisher()
        creds = PublisherCredentials(platform="mock")
        
        # 認証
        result = await publisher.authenticate(creds)
        assert result is True
        assert publisher.auth_called
        
        # 投稿
        result = await publisher.publish({}, {}, creds)
        assert result.success is True
        assert result.post_id == "123"
        assert publisher.publish_called
        
        # 更新
        result = await publisher.update_chapter("123", {}, creds)
        assert result.success is True
        assert publisher.update_called
        
        # ステータス取得
        status = await publisher.get_post_status("123", creds)
        assert status["post_id"] == "123"
        assert publisher.status_called
    
    def test_publisher_adapter_abstract(self):
        """PublisherAdapterが抽象クラスであること確認"""
        with pytest.raises(TypeError):
            PublisherAdapter()  # 直接インスタンス化不可


if __name__ == "__main__":
    pytest.main([__file__, "-v"])