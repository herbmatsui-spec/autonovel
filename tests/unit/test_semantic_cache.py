"""Unit tests for src/services/semantic_cache.py - Semantic cache with L1/L2 caching."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import datetime

from src.services.semantic_cache import SemanticCacheManager


class TestSemanticCacheManager:
    """Tests for SemanticCacheManager class."""

    def setup_method(self):
        self.mock_vector_store = MagicMock()
        self.mock_client = MagicMock()

        self.cache = SemanticCacheManager(
            vector_store=self.mock_vector_store,
            client=self.mock_client,
            embedding_model="test-embedding",
        )

    def test_get_l1_key(self):
        """Test L1 cache key generation."""
        key = self.cache._get_l1_key("prompt", "generation", "fantasy", 0.7)
        assert len(key) == 64  # SHA256 hex

        # Same inputs produce same key
        key2 = self.cache._get_l1_key("prompt", "generation", "fantasy", 0.7)
        assert key == key2

        # Different inputs produce different keys
        key3 = self.cache._get_l1_key("prompt", "generation", "fantasy", 0.8)
        assert key != key3

    @pytest.mark.asyncio
    async def test_get_embedding_success(self):
        """Test successful embedding generation."""
        mock_response = MagicMock()
        mock_response.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]

        with patch.object(self.cache, '_call_embedding_api', new=AsyncMock(return_value=mock_response)):
            vec = await self.cache._get_embedding("test text")

        assert vec == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_get_embedding_l2b_cache_hit(self):
        """Test L2-B embedding cache hit."""
        cached_vec = [0.1, 0.2, 0.3]
        text_hash = "test_hash"
        self.cache._l2_embedding_cache[text_hash] = cached_vec

        with patch("hashlib.sha256") as mock_sha:
            mock_hash = MagicMock()
            mock_hash.hexdigest.return_value = text_hash
            mock_sha.return_value = mock_hash

            vec = await self.cache._get_embedding("test text")

        assert vec == cached_vec

    @pytest.mark.asyncio
    async def test_get_embedding_failure(self):
        """Test embedding generation failure."""
        with patch.object(self.cache, '_call_embedding_api', new=AsyncMock(side_effect=Exception("API error"))):
            vec = await self.cache._get_embedding("test text")

        assert vec == []

    @pytest.mark.asyncio
    async def test_search_l1_hit(self):
        """Test search with L1 cache hit."""
        self.cache._l1_cache["test_key"] = "cached_response"

        result = await self.cache.search(
            prompt="test",
            task_type="generation",
            genre="fantasy",
            temperature=0.7,
        )

        assert result == "cached_response"

    @pytest.mark.asyncio
    async def test_search_no_vector_store(self):
        """Test search when vector store unavailable."""
        self.cache.vector_store = None

        result = await self.cache.search("test", "generation")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_no_client(self):
        """Test search when client unavailable."""
        self.cache.client = None

        result = await self.cache.search("test", "generation")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_vector_hit(self):
        """Test successful vector search hit."""
        self.cache._get_embedding = AsyncMock(return_value=[0.1, 0.2])

        mock_result = {
            "id": "doc1",
            "content": '{"response": "cached"}',
            "metadata": {
                "task_type": "generation",
                "genre": "fantasy",
                "input_length": 100,
                "is_json": True,
                "last_accessed": datetime.datetime.now().isoformat(),
            },
            "distance": 0.01,  # High similarity
        }
        self.mock_vector_store.search = AsyncMock(return_value=[mock_result])

        result = await self.cache.search(
            prompt="test prompt",
            task_type="generation",
            genre="fantasy",
            threshold=0.95,
        )

        assert result == {"response": "cached"}

    @pytest.mark.asyncio
    async def test_search_vector_miss_distance(self):
        """Test search miss due to distance threshold."""
        self.cache._get_embedding = AsyncMock(return_value=[0.1, 0.2])

        mock_result = {
            "id": "doc1",
            "content": "response",
            "metadata": {
                "task_type": "generation",
                "genre": "fantasy",
                "input_length": 100,
                "is_json": False,
            },
            "distance": 0.2,  # Low similarity (> 0.05 for threshold 0.95)
        }
        self.mock_vector_store.search = AsyncMock(return_value=[mock_result])

        result = await self.cache.search(
            prompt="test prompt",
            task_type="generation",
            genre="fantasy",
            threshold=0.95,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_search_vector_miss_length_diff(self):
        """Test search miss due to input length difference."""
        self.cache._get_embedding = AsyncMock(return_value=[0.1, 0.2])

        mock_result = {
            "id": "doc1",
            "content": "response",
            "metadata": {
                "task_type": "generation",
                "genre": "fantasy",
                "input_length": 1000,  # Very different from prompt length
                "is_json": False,
            },
            "distance": 0.01,
        }
        self.mock_vector_store.search = AsyncMock(return_value=[mock_result])

        result = await self.cache.search(
            prompt="short",  # Length ~5
            task_type="generation",
            genre="fantasy",
            threshold=0.95,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_add(self):
        """Test adding to cache."""
        self.cache._get_embedding = AsyncMock(return_value=[0.1, 0.2])
        self.mock_vector_store.get_collection = MagicMock()
        self.mock_vector_store.add_documents = AsyncMock()

        await self.cache.add(
            prompt="test prompt",
            response={"key": "value"},
            task_type="generation",
            genre="fantasy",
            temperature=0.7,
        )

        # Check L1 cache
        l1_key = self.cache._get_l1_key("test prompt", "generation", "fantasy", 0.7)
        assert self.cache._l1_cache[l1_key] == {"key": "value"}

        # Check vector store add called
        self.mock_vector_store.add_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_string_response(self):
        """Test adding string (non-JSON) response."""
        self.cache._get_embedding = AsyncMock(return_value=[0.1, 0.2])
        self.mock_vector_store.get_collection = MagicMock()
        self.mock_vector_store.add_documents = AsyncMock()

        await self.cache.add(
            prompt="test",
            response="plain text response",
            task_type="generation",
        )

        # Check metadata has is_json=False
        call_args = self.mock_vector_store.add_documents.call_args
        metadatas = call_args.kwargs["metadatas"]
        assert metadatas[0]["is_json"] is False

    @pytest.mark.asyncio
    async def test_evict_if_needed(self):
        """Test LRU eviction when cache exceeds max size."""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": [f"id_{i}" for i in range(1500)],
            "metadatas": [
                {"last_accessed": f"2024-01-{i:02d}T00:00:00"} for i in range(1, 1501)
            ],
        }
        self.mock_vector_store.get_collection.return_value = mock_collection
        self.mock_vector_store.delete_by_id = AsyncMock()

        await self.cache.evict_if_needed(max_items=1000)

        self.mock_vector_store.delete_by_id.assert_called_once()
        deleted_ids = self.mock_vector_store.delete_by_id.call_args[0][1]
        assert len(deleted_ids) == 500  # 1500 - 1000

    @pytest.mark.asyncio
    async def test_evict_if_needed_under_limit(self):
        """Test no eviction when under limit."""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["id1", "id2"],
            "metadatas": [
                {"last_accessed": "2024-01-01T00:00:00"},
                {"last_accessed": "2024-01-02T00:00:00"},
            ],
        }
        self.mock_vector_store.get_collection.return_value = mock_collection

        await self.cache.evict_if_needed(max_items=1000)

        self.mock_vector_store.delete_by_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_prefetch_next(self):
        """Test prefetching next episode prompts."""
        with patch("src.services.semantic_cache.PromptManager") as mock_pm_class:
            mock_pm = MagicMock()
            mock_pm.build_drafting_prompt = AsyncMock(return_value="drafting prompt")
            mock_pm.build_polishing_prompt = AsyncMock(return_value="polishing prompt")
            mock_pm_class.return_value = mock_pm

            self.cache._prefetch_embedding = AsyncMock()

            await self.cache.prefetch_next(
                book_id=1,
                current_ep_num=5,
                task_types=["drafting", "polishing"],
                genre="fantasy",
            )

            mock_pm.build_drafting_prompt.assert_called_once()
            mock_pm.build_polishing_prompt.assert_called_once()
            assert self.cache._prefetch_embedding.call_count == 2

    @pytest.mark.asyncio
    async def test_prefetch_by_pattern(self):
        """Test batch prefetch by episode range."""
        self.cache.prefetch_next = AsyncMock(return_value=None)

        result = await self.cache.prefetch_by_pattern(
            book_id=1,
            ep_range_start=5,
            ep_range_end=7,
            task_types=["drafting"],
        )

        assert result["total"] == 3
        assert result["succeeded"] == 3
        assert result["failed"] == 0
        assert self.cache.prefetch_next.call_count == 3

    @pytest.mark.asyncio
    async def test_get_cache_warmth(self):
        """Test cache warmth metrics."""
        self.cache._l1_cache = MagicMock()
        self.cache._l1_cache.__len__ = MagicMock(return_value=500)
        self.cache._l1_cache.maxsize = 1000

        self.cache._l2_embedding_cache = MagicMock()
        self.cache._l2_embedding_cache.__len__ = MagicMock(return_value=250)
        self.cache._l2_embedding_cache.maxsize = 500

        warmth = await self.cache.get_cache_warmth("generation", "fantasy")

        assert warmth["l1_size"] == 500
        assert warmth["l1_max"] == 1000
        assert warmth["l2_size"] == 250
        assert warmth["l2_max"] == 500
        assert 0 <= warmth["warmth_score"] <= 1

    @pytest.mark.asyncio
    async def test_compute_similarity_identical(self):
        """Test similarity of identical texts."""
        sim = await self.cache.compute_similarity("same text", "same text")
        assert sim == 1.0

    @pytest.mark.asyncio
    async def test_compute_similarity_different(self):
        """Test similarity of different texts."""
        self.cache._get_embedding = AsyncMock(side_effect=[
            [1.0, 0.0, 0.0],  # vec1
            [0.0, 1.0, 0.0],  # vec2
        ])

        sim = await self.cache.compute_similarity("text1", "text2")
        assert sim == 0.0  # Orthogonal vectors

    @pytest.mark.asyncio
    async def test_compute_similarity_zero_norm(self):
        """Test similarity with zero norm vectors."""
        self.cache._get_embedding = AsyncMock(side_effect=[
            [0.0, 0.0],  # Zero vector
            [1.0, 0.0],
        ])

        sim = await self.cache.compute_similarity("text1", "text2")
        assert sim == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])