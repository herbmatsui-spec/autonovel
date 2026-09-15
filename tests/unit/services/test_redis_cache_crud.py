import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.redis_cache import RedisCacheService

@pytest.mark.asyncio
async def test_redis_cache_set_and_get():
    service = RedisCacheService(namespace="test_ns")
    mock_client = AsyncMock()
    mock_client.get.return_value = json.dumps({"title": "novel"}).encode("utf-8")
    service._client = mock_client
    
    val = await service.get("key1")
    assert val is not None
    mock_client.get.assert_awaited_once_with("test_ns:key1")

@pytest.mark.asyncio
async def test_redis_cache_delete():
    service = RedisCacheService(namespace="test_ns")
    mock_client = AsyncMock()
    service._client = mock_client
    
    await service.delete("key1")
    mock_client.delete.assert_awaited_once_with("test_ns:key1")
