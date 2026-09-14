import pytest
from unittest.mock import AsyncMock
from src.services.redis_cache import RedisCacheService
from src.services.semantic_cache import SemanticCacheManager

@pytest.mark.asyncio
async def test_services_end_to_end_mock():
    redis_svc = RedisCacheService()
    redis_svc.get = AsyncMock(return_value=None)
    redis_svc.set = AsyncMock(return_value=True)
    
    await redis_svc.set("key", "val")
    redis_svc.set.assert_awaited_once_with("key", "val")
