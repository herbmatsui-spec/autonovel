"""Unit tests for src/services/redis_cache.py - Redis distributed cache service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Mock redis.asyncio before importing the module
with patch.dict('sys.modules', {'redis.asyncio': MagicMock()}):
    from src.services.redis_cache import RedisCacheService, PromptCacheService, REDIS_AVAILABLE


class TestRedisCacheService:
    """Tests for RedisCacheService class."""

    def setup_method(self):
        # Mock REDIS_AVAILABLE to True
        self.redis_patcher = patch('src.services.redis_cache.REDIS_AVAILABLE', True)
        self.mock_redis_module = self.redis_patcher.start()
        
        # Mock redis.asyncio
        self.mock_redis_asyncio = MagicMock()
        import sys
        sys.modules['redis.asyncio'] = self.mock_redis_asyncio
        
        self.cache = RedisCacheService(
            redis_url="redis://localhost:6379/0",
            namespace="test:cache",
            default_ttl=3600,
        )

    def teardown_method(self):
        self.redis_patcher.stop()

    @pytest.mark.asyncio
    async def test_make_key(self):
        """Test key generation with namespace."""
        key = self.cache._make_key("test_key")
        assert key == "test:cache:test_key"

    def test_serialize_primitives(self):
        """Test serialization of primitive types."""
        assert self.cache._serialize("string") == '"string"'
        assert self.cache._serialize(123) == "123"
        assert self.cache._serialize(1.5) == "1.5"
        assert self.cache._serialize(True) == "true"
        assert self.cache._serialize(None) == "null"

    def test_serialize_complex(self):
        """Test serialization of complex types."""
        data = {"key": "value", "list": [1, 2, 3]}
        result = self.cache._serialize(data)
        parsed = json.loads(result)
        assert parsed["key"] == "value"
        assert parsed["list"] == [1, 2, 3]

    def test_deserialize_valid_json(self):
        """Test deserialization of valid JSON."""
        result = self.cache._deserialize('{"key": "value"}')
        assert result == {"key": "value"}

    def test_deserialize_invalid_json(self):
        """Test deserialization of invalid JSON returns raw string."""
        result = self.cache._deserialize("not json")
        assert result == "not json"

    @pytest.mark.asyncio
    async def test_get_miss(self):
        """Test cache miss."""
        self.cache._client = AsyncMock()
        self.cache._client.get = AsyncMock(return_value=None)

        result = await self.cache.get("missing_key")
        assert result is None
        self.cache._client.get.assert_called_once_with("test:cache:missing_key")

    @pytest.mark.asyncio
    async def test_get_hit(self):
        """Test cache hit."""
        self.cache._client = AsyncMock()
        self.cache._client.get = AsyncMock(return_value='{"data": "value"}')

        result = await self.cache.get("existing_key")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_get_no_client(self):
        """Test get when Redis is not available."""
        self.cache._client = None
        result = await self.cache.get("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_success(self):
        """Test successful cache set."""
        self.cache._client = AsyncMock()
        self.cache._client.set = AsyncMock(return_value=True)

        result = await self.cache.set("key", {"data": "value"}, ttl=100)
        assert result is True
        self.cache._client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_nx_xx(self):
        """Test set with nx and xx flags."""
        self.cache._client = AsyncMock()
        self.cache._client.set = AsyncMock(return_value=True)

        await self.cache.set("key", "value", nx=True)
        call_args = self.cache._client.set.call_args
        assert call_args.kwargs["nx"] is True

        await self.cache.set("key", "value", xx=True)
        call_args = self.cache._client.set.call_args
        assert call_args.kwargs["xx"] is True

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test cache delete."""
        self.cache._client = AsyncMock()
        self.cache._client.delete = AsyncMock(return_value=1)

        result = await self.cache.delete("key")
        assert result is True

    @pytest.mark.asyncio
    async def test_exists(self):
        """Test key existence check."""
        self.cache._client = AsyncMock()
        self.cache._client.exists = AsyncMock(return_value=1)

        result = await self.cache.exists("key")
        assert result is True

    @pytest.mark.asyncio
    async def test_expire(self):
        """Test TTL update."""
        self.cache._client = AsyncMock()
        self.cache._client.expire = AsyncMock(return_value=True)

        result = await self.cache.expire("key", 200)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_ttl(self):
        """Test getting TTL."""
        self.cache._client = AsyncMock()
        self.cache._client.ttl = AsyncMock(return_value=100)

        result = await self.cache.get_ttl("key")
        assert result == 100

    @pytest.mark.asyncio
    async def test_invalidate_pattern(self):
        """Test pattern-based invalidation."""
        self.cache._client = AsyncMock()
        mock_keys = ["test:cache:key1", "test:cache:key2"]
        # Create async iterator for scan_iter
        async def mock_scan_iter(match, count):
            for key in mock_keys:
                yield key
        self.cache._client.scan_iter = mock_scan_iter
        self.cache._client.delete = AsyncMock(return_value=1)

        result = await self.cache.invalidate_pattern("key*")
        assert result == 2

    @pytest.mark.asyncio
    async def test_mget(self):
        """Test multiple key get."""
        self.cache._client = AsyncMock()
        self.cache._client.mget = AsyncMock(return_value=['{"a": 1}', None, '{"b": 2}'])

        result = await self.cache.mget(["key1", "key2", "key3"])
        assert result == {"key1": {"a": 1}, "key3": {"b": 2}}

    @pytest.mark.asyncio
    async def test_mset(self):
        """Test multiple key set."""
        self.cache._client = AsyncMock()
        mock_pipe = AsyncMock()
        self.cache._client.pipeline = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(return_value=[True, True])

        result = await self.cache.mset({"key1": "val1", "key2": "val2"})
        assert result is True

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        self.cache._client = AsyncMock()
        self.cache._client.ping = AsyncMock(return_value=True)

        result = await self.cache.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing connection pool."""
        mock_pool = AsyncMock()
        self.cache._pool = mock_pool
        self.cache._client = AsyncMock()

        await self.cache.close()
        mock_pool.disconnect.assert_called_once()


class TestPromptCacheService:
    """Tests for PromptCacheService class."""

    def setup_method(self):
        self.mock_redis = AsyncMock(spec=RedisCacheService)
        self.mock_semantic = AsyncMock()
        self.mock_l1 = {}

        self.cache = PromptCacheService(
            redis_cache=self.mock_redis,
            semantic_cache=self.mock_semantic,
            l1_cache=self.mock_l1,
        )

    def test_generate_cache_key(self):
        """Test cache key generation."""
        key = self.cache._generate_cache_key(
            template_name="drafting",
            prompt_hash="abc123",
            model_id="gemini-2.5-pro",
            template_version="1.0",
        )
        assert key == "prompt:drafting:gemini-2.5-pro:1.0:abc123"

    def test_compute_prompt_hash(self):
        """Test deterministic prompt hash computation."""
        hash1 = PromptCacheService.compute_prompt_hash("prompt", param1="value1", param2="value2")
        hash2 = PromptCacheService.compute_prompt_hash("prompt", param2="value2", param1="value1")
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_get_ttl_by_task_type(self):
        """Test TTL retrieval by task type."""
        assert self.cache._get_ttl("generation") == 7 * 24 * 3600
        assert self.cache._get_ttl("plot_expansion") == 14 * 24 * 3600
        assert self.cache._get_ttl("unknown") == 7 * 24 * 3600  # default
        assert self.cache._get_ttl("generation", custom_ttl=100) == 100

    @pytest.mark.asyncio
    async def test_get_l1_hit(self):
        """Test L1 cache hit."""
        l1_key = "prompt:test:model:1.0:hash:generation:general:0.7"
        self.mock_l1[l1_key] = "cached_response"

        # Need to mock the key generation
        with patch.object(self.cache, '_generate_cache_key', return_value="prompt:test:model:1.0:hash"):
            with patch.object(self.cache, 'compute_prompt_hash', return_value="hash"):
                result = await self.cache.get(
                    template_name="test",
                    prompt="test prompt",
                    model_id="model",
                    task_type="generation",
                )
        assert result == "cached_response"

    @pytest.mark.asyncio
    async def test_get_l2_hit(self):
        """Test L2 (Redis) cache hit."""
        self.mock_redis.get = AsyncMock(return_value="redis_response")

        with patch.object(self.cache, '_generate_cache_key', return_value="prompt:test:model:1.0:hash"):
            with patch.object(self.cache, 'compute_prompt_hash', return_value="hash"):
                result = await self.cache.get(
                    template_name="test",
                    prompt="test prompt",
                    model_id="model",
                    task_type="generation",
                )
        assert result == "redis_response"

    @pytest.mark.asyncio
    async def test_get_l3_hit(self):
        """Test L3 (semantic) cache hit."""
        self.mock_redis.get = AsyncMock(return_value=None)
        self.mock_semantic.search = AsyncMock(return_value="semantic_response")

        with patch.object(self.cache, '_generate_cache_key', return_value="prompt:test:model:1.0:hash"):
            with patch.object(self.cache, 'compute_prompt_hash', return_value="hash"):
                result = await self.cache.get(
                    template_name="test",
                    prompt="test prompt",
                    model_id="model",
                    task_type="generation",
                )
        assert result == "semantic_response"

    @pytest.mark.asyncio
    async def test_get_miss(self):
        """Test cache miss at all levels."""
        self.mock_redis.get = AsyncMock(return_value=None)
        self.mock_semantic.search = AsyncMock(return_value=None)

        with patch.object(self.cache, '_generate_cache_key', return_value="prompt:test:model:1.0:hash"):
            with patch.object(self.cache, 'compute_prompt_hash', return_value="hash"):
                result = await self.cache.get(
                    template_name="test",
                    prompt="test prompt",
                    model_id="model",
                    task_type="generation",
                )
        assert result is None

    @pytest.mark.asyncio
    async def test_set_stores_all_layers(self):
        """Test set stores in all cache layers."""
        self.mock_redis.set = AsyncMock()
        self.mock_semantic.add = AsyncMock()

        with patch.object(self.cache, '_generate_cache_key', return_value="prompt:test:model:1.0:hash"):
            with patch.object(self.cache, 'compute_prompt_hash', return_value="hash"):
                await self.cache.set(
                    template_name="test",
                    prompt="test prompt",
                    response="response",
                    model_id="model",
                    task_type="generation",
                )

        assert "prompt:test:model:1.0:hash:generation:general:0.7" in self.mock_l1
        self.mock_redis.set.assert_called_once()
        self.mock_semantic.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_book(self):
        """Test book-specific cache invalidation."""
        self.mock_redis.invalidate_pattern = AsyncMock(return_value=5)

        result = await self.cache.invalidate_book(123)
        assert result == 5
        self.mock_redis.invalidate_pattern.assert_called_with("*:book:123:*")

    @pytest.mark.asyncio
    async def test_invalidate_template(self):
        """Test template-specific cache invalidation."""
        self.mock_redis.invalidate_pattern = AsyncMock(return_value=3)

        result = await self.cache.invalidate_template("drafting")
        assert result == 3
        self.mock_redis.invalidate_pattern.assert_called_with("prompt:drafting:*")

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test statistics retrieval."""
        self.mock_redis.health_check = AsyncMock(return_value=True)
        self.mock_l1["key1"] = "val1"

        stats = await self.cache.get_stats()
        assert stats["l1_size"] == 1
        assert stats["redis_connected"] is True
        assert stats["semantic_available"] is True
        assert "ttl_policies" in stats

    @pytest.mark.asyncio
    async def test_warm_cache(self):
        """Test cache warming."""
        self.mock_redis.set = AsyncMock()
        self.mock_semantic.add = AsyncMock()

        entries = [
            {"template_name": "test", "prompt": "p1", "response": "r1", "model_id": "m1"},
            {"template_name": "test", "prompt": "p2", "response": "r2", "model_id": "m1"},
        ]

        with patch.object(self.cache, '_generate_cache_key', return_value="prompt:test:model:1.0:hash"):
            with patch.object(self.cache, 'compute_prompt_hash', return_value="hash"):
                result = await self.cache.warm_cache(entries, task_type="generation")
        assert result == 2

    @pytest.mark.asyncio
    async def test_prefetch_next_episodes(self):
        """Test next episode prefetch preparation."""
        result = await self.cache.prefetch_next_episodes(
            book_id=1,
            current_ep=5,
            next_ep_count=3,
        )
        assert result == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])