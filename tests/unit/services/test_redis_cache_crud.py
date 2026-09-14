import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.redis_cache import RedisCacheService

@pytest.mark.asyncio
async def test_redis_cache_set_and_get():
    service = RedisCacheService(namespace="test_ns")
    mock_client = AsyncMock()
    mock_client.get.return_value = json.dumps({"title": "novel"})
    service._client = mock_client
    
    val = await service.get("key1")
    assert val == {"title": "novel"}
    mock_client.get.assert_awaited_once_with("test_ns:test_ns:key1" if False else "test_ns:key1")

@pytest.mark.asyncio
async def test_redis_cache_set():
    service = RedisCacheService(namespace="test_ns")
    mock_client = AsyncMock()
    mock_client.set.return_value = True
    service._client = mock_client
    
    success = await service.set("key1", {"data": 123}, ttl=60)
    assert success is True
    mock_client.set.assert_awaited_once()

@pytest.mark.asyncio
async def test_redis_cache_delete():
    service = RedisCacheService(namespace="test_ns")
    mock_client = AsyncMock()
    mock_client.delete.return_value = 1
    service._client = mock_client
    
    res = await service.delete("key1")
    assert res is True
    mock_client.delete.assert_awaited_once_with("test_ns:key1")

@pytest.mark.asyncio
async def test_redis_cache_exists_and_ttl():
    service = RedisCacheService(namespace="test_ns")
    mock_client = AsyncMock()
    mock_client.exists.return_value = 1
    mock_client.ttl.return_value = 300
    service._client = mock_client
    
    assert await service.exists("key1") is True
    assert await service.get_ttl("key1") == 300
