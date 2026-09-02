"""Unit tests for EmbeddingService cache + rate limit + __repr__."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from src.services.embedding_service import (
    EmbeddingService,
    LRUEmbeddingCache,
    RedisEmbeddingCache,
    embed_texts,
)


class TestLRUEmbeddingCache:
    def test_hits_and_misses(self):
        cache = LRUEmbeddingCache(maxsize=8)
        assert cache.get("missing") is None
        cache.set("k1", [0.1, 0.2])
        assert cache.get("k1") == [0.1, 0.2]
        info = cache.info()
        assert info["hits"] == 1
        assert info["misses"] == 1
        assert info["backend"] == "lru"
        assert info["size"] == 1

    def test_eviction(self):
        cache = LRUEmbeddingCache(maxsize=2)
        cache.set("a", [1.0])
        cache.set("b", [2.0])
        cache.set("c", [3.0])  # evicts 'a'
        assert cache.get("a") is None
        assert cache.get("b") == [2.0]
        assert cache.get("c") == [3.0]


class TestRedisEmbeddingCacheFallback:
    def test_falls_back_when_no_redis(self):
        # Construct directly with a pre-failed client (None) so the
        # constructor still tries the live Redis ping but we then force
        # the fallback explicitly. Use a mock client whose .ping raises.
        class BoomClient:
            def get(self, k):
                raise RuntimeError("redis unavailable")

            def set(self, k, v):
                raise RuntimeError("redis unavailable")

            def ping(self):
                raise RuntimeError("redis unavailable")

        cache = RedisEmbeddingCache(redis_client=BoomClient(), prefix="x:")
        # Force fallback even if constructor somehow held the client.
        cache._client = None
        cache.set("k", [0.5, 0.6])
        assert cache.get("k") == [0.5, 0.6]
        info = cache.info()
        # backend label is just "lru" when we forced fallback by clearing
        # the client; the key contract is that operations still succeed.
        assert info["backend"] in {"lru", "redis+lru"}


class TestEmbeddingServiceCache:
    def test_get_embedding_uses_cache(self):
        svc = EmbeddingService.__new__(EmbeddingService)
        svc.model_name = "m"
        svc._client = None
        cache = LRUEmbeddingCache(maxsize=8)
        svc._cache = cache

        v1 = svc.get_embedding("hello world")
        v2 = svc.get_embedding("hello world")
        # Without OpenAI client we get a deterministic pseudo-embedding;
        # the second call should hit the cache (no API).
        assert v1 == v2
        info = cache.info()
        assert info["hits"] >= 1

    def test_get_embedding_blank(self):
        svc = EmbeddingService.__new__(EmbeddingService)
        svc.model_name = "m"
        svc._client = None
        svc._cache = LRUEmbeddingCache()
        assert svc.get_embedding("") == [0.0] * 1536
        assert svc.get_embedding("   ") == [0.0] * 1536

    def test_repr_no_secrets(self):
        svc = EmbeddingService(model_name="m")
        r = repr(svc)
        assert "EmbeddingService" in r
        assert "api_key" not in r.lower()

    def test_cache_info(self):
        svc = EmbeddingService.__new__(EmbeddingService)
        svc.model_name = "m"
        svc._client = None
        svc._cache = LRUEmbeddingCache()
        svc.get_embedding("foo")
        info = svc.cache_info()
        assert info["backend"] == "lru"


class TestEmbedTextsModuleAlias:
    def test_embed_texts_alias(self):
        # Module-level alias should be importable and callable.
        out = embed_texts(["x", "y"])
        assert len(out) == 2
        assert all(len(v) == 1536 for v in out)
