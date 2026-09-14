import pytest
from unittest.mock import AsyncMock, patch
from src.services.retry_decorator import with_llm_retry

@pytest.mark.asyncio
async def test_async_retry_decorator():
    mock_func = AsyncMock(side_effect=[Exception("503 Service Unavailable"), "成功"])
    
    class MockService:
        @with_llm_retry()
        async def run(self, max_retries=2, **kwargs):
            return await mock_func()

    svc = MockService()
    with patch("asyncio.sleep", new_callable=AsyncMock):
        res = await svc.run(max_retries=2)
        assert res == "成功"
        assert mock_func.call_count == 2
