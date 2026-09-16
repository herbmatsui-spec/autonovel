import pytest
from unittest.mock import AsyncMock
from src.services.redis_cache import RedisCacheService

@pytest.mark.asyncio
async def test_redis_cache_connection_error_safe_get():
    service = RedisCacheService()
    mock_client = AsyncMock()
    mock_client.get.side_effect = ConnectionError("Redis is down")
    service._client = mock_client

    # 接続エラー時でも例外を出さずNoneを返す設計であること
    res = await service.get("some_key")
    assert res is None
