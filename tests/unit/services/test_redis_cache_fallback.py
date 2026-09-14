import pytest
from unittest.mock import AsyncMock
from src.services.redis_cache import RedisCacheService

@pytest.mark.asyncio
async def test_redis_cache_connection_error_safe_get():
    service = RedisCacheService()
    mock_client = AsyncMock()
    mock_client.get.side_effect = ConnectionError("Redis is down")
    service._client = mock_client
    
    res = await service.get("some_key")
    assert res is None

@pytest.mark.asyncio
async def test_redis_cache_connection_error_safe_set():
    service = RedisCacheService()
    mock_client = AsyncMock()
    mock_client.set.side_effect = ConnectionError("Redis is down")
    service._client = mock_client
    
    res = await service.set("some_key", "val")
    assert res is False

@pytest.mark.asyncio
async def test_redis_cache_connection_error_safe_delete():
    service = RedisCacheService()
    mock_client = AsyncMock()
    mock_client.delete.side_effect = ConnectionError("Redis is down")
    service._client = mock_client
    
    res = await service.delete("some_key")
    assert res is False
