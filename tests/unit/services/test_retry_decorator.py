from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.exceptions import (
    LLMTemporaryError,
    LLMUnrecoverableError,
)
from src.services.retry_decorator import with_llm_retry


@pytest.mark.asyncio
async def test_async_retry_decorator_success_after_retry():
    class MockService:
        def __init__(self):
            self.cooldown = MagicMock()
            self.cooldown.wait = AsyncMock()
            self._lock = None
            self._active_requests = 0
            self._consecutive_5xx = 0
            self.mock_func = AsyncMock(side_effect=[ValueError("503 Service Unavailable"), "成功"])

        @with_llm_retry()
        async def target_method(self, retry_state=None):
            return await self.mock_func()

    service = MockService()

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        res = await service.target_method()
        assert res == "成功"
        assert service.mock_func.call_count == 2
        mock_sleep.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_retry_decorator_non_retryable_fail_fast():
    class MockService:
        def __init__(self):
            self.cooldown = None
            self._lock = None
            self._active_requests = 0
            self._consecutive_5xx = 0
            self.mock_func = AsyncMock(side_effect=ValueError("404 Not Found"))

        @with_llm_retry()
        async def target_method(self, retry_state=None):
            return await self.mock_func()

    service = MockService()

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(LLMUnrecoverableError):
            await service.target_method()
    assert service.mock_func.call_count == 1


@pytest.mark.asyncio
async def test_async_retry_decorator_max_retries_exceeded():
    class MockService:
        def __init__(self):
            self.cooldown = None
            self._lock = None
            self._active_requests = 0
            self._consecutive_5xx = 0
            self.mock_func = AsyncMock(side_effect=ValueError("429 rate limit exceeded"))

        @with_llm_retry()
        async def target_method(self, max_retries: int = 2, retry_state=None):
            return await self.mock_func()

    service = MockService()

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(LLMTemporaryError):
            await service.target_method(max_retries=2)
    assert service.mock_func.call_count == 2
