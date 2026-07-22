import pytest

from src.core.container import AppContainer
from src.services.redis_cache import RedisCacheService, PromptCacheService


def test_app_container_returns_redis_cache():
    container = AppContainer()
    svc = container.redis_cache()
    assert isinstance(svc, RedisCacheService)


def test_app_container_returns_prompt_cache():
    container = AppContainer()
    svc = container.prompt_cache()
    assert isinstance(svc, PromptCacheService)
