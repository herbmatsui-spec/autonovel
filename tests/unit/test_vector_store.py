"""Unit tests for src/services/vector_store.py - ChromaDB vector store with BM25 hybrid search."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.vector_store import (
    BaseVectorStore,
    CollectionType,
    CollectionConfig,
    DEFAULT_COLLECTIONS,
    ChromaClientProvider,
    ChromaVectorStore,
)


class TestCollectionType:
    """Tests for CollectionType enum."""

    def test_collection_types_exist(self):
        """Test all expected collection types exist."""
        assert CollectionType.SEMANTIC_CACHE.value == "semantic_cache"
        assert CollectionType.STYLE_MEMORY.value == "style_memory"
        assert CollectionType.WORLD_MEMORY.value == "world_memory"
        assert CollectionType.CHARACTER_MEMORY.value == "character_memory"
        assert CollectionType.NARRATIVE_MEMORY.value == "narrative_memory"
        assert CollectionType.EPISODE_MEMORY.value == "episode_memory"


class TestCollectionConfig:
    """Tests for CollectionConfig class."""

    def test_default_config(self):
        """Test default collection config."""
        config = CollectionConfig(name="test", space="cosine")
        assert config.name == "test"
        assert config.space == "cosine"
        assert config.description == ""
        assert config.metadata_schema == {}

    def test_custom_hnsw_params(self):
        """Test custom HNSW parameters."""
        config = CollectionConfig(
            name="test",
            hnsw_params={"hnsw:construction_ef": 200, "hnsw:M": 32},
        )
        assert config.hnsw_params["hnsw:construction_ef"] == 200
        assert config.hnsw_params["hnsw:M"] == 32

    def test_get_metadata(self):
        """Test metadata generation for ChromaDB."""
        config = CollectionConfig(name="test", space="cosine", description="Test desc")
        meta = config.get_metadata()
        assert meta["hnsw:space"] == "cosine"
        assert meta["description"] == "Test desc"
        assert "hnsw:construction_ef" in meta


class TestDEFAULT_COLLECTIONS:
    """Tests for DEFAULT_COLLECTIONS configuration."""

    def test_all_types_configured(self):
        """Test all collection types have default configs."""
        for ctype in CollectionType:
            assert ctype in DEFAULT_COLLECTIONS
            config = DEFAULT_COLLECTIONS[ctype]
            assert config.name == ctype.value
            assert config.space == "cosine"

    def test_metadata_schemas_defined(self):
        """Test metadata schemas are properly defined."""
        for ctype in CollectionType:
            config = DEFAULT_COLLECTIONS[ctype]
            assert isinstance(config.metadata_schema, dict)
            assert len(config.metadata_schema) > 0


class TestChromaClientProvider:
    """Tests for ChromaClientProvider class."""

    def setup_method(self):
        self.provider = ChromaClientProvider(db_path="./test_chroma_db")

    @patch("src.services.vector_store.chromadb.PersistentClient")
    def test_get_client_success(self, mock_client_class):
        """Test successful client initialization."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        client = self.provider.get_client()
        assert client == mock_client
        mock_client_class.assert_called_once_with(path="./test_chroma_db")

    @patch("src.services.vector_store.chromadb.PersistentClient")
    def test_get_client_retry(self, mock_client_class):
        """Test client initialization with retries."""
        mock_client_class.side_effect = [Exception("fail"), Exception("fail"), MagicMock()]

        with patch("time.sleep"):
            client = self.provider.get_client(retries=3, base_delay=0.01)

        assert client is not None
        assert mock_client_class.call_count == 3

    @patch("src.services.vector_store.chromadb.PersistentClient")
    def test_get_client_all_retries_fail(self, mock_client_class):
        """Test client initialization when all retries fail."""
        mock_client_class.side_effect = Exception("persistent fail")

        with patch("time.sleep"):
            client = self.provider.get_client(retries=2, base_delay=0.01)

        assert client is None

    def test_close(self):
        """Test client close."""
        self.provider._client = MagicMock()
        self.provider.close()
        assert self.provider._client is None


class TestChromaVectorStore:
    """Tests for ChromaVectorStore class."""

    def setup_method(self):
        self.mock_provider = MagicMock(spec=ChromaClientProvider)
        self.mock_client = MagicMock()
        self.mock_provider.get_client.return_value = self.mock_client
        self.store = ChromaVectorStore(self.mock_provider)

    def test_client_property(self):
        """Test client property returns provider client."""
        assert self.store.client == self.mock_client

    def test_initialize_collections(self):
        """Test collection initialization."""
        mock_collection = MagicMock()
        self.mock_client.get_or_create_collection.return_value = mock_collection

        results = self.store.initialize_collections([
            CollectionType.SEMANTIC_CACHE,
            CollectionType.STYLE_MEMORY,
        ])

        assert results["semantic_cache"] is True
        assert results["style_memory"] is True
        assert self.mock_client.get_or_create_collection.call_count == 2

    def test_ensure_collection_existing(self):
        """Test ensuring existing collection."""
        mock_collection = MagicMock()
        mock_collection.metadata = {"hnsw:space": "cosine"}
        self.mock_client.get_collection.return_value = mock_collection

        config = DEFAULT_COLLECTIONS[CollectionType.SEMANTIC_CACHE]
        result = self.store._ensure_collection(config)

        assert result is True
        self.mock_client.get_collection.assert_called_once()

    def test_ensure_collection_create_new(self):
        """Test creating new collection."""
        self.mock_client.get_collection.side_effect = Exception("Not found")
        mock_collection = MagicMock()
        self.mock_client.get_or_create_collection.return_value = mock_collection

        config = DEFAULT_COLLECTIONS[CollectionType.SEMANTIC_CACHE]
        result = self.store._ensure_collection(config)

        assert result is True
        self.mock_client.get_or_create_collection.assert_called_once()

    def test_ensure_collection_no_client(self):
        """Test ensure collection when no client available."""
        self.mock_provider.get_client.return_value = None

        config = DEFAULT_COLLECTIONS[CollectionType.SEMANTIC_CACHE]
        result = self.store._ensure_collection(config)

        assert result is False

    def test_get_collection(self):
        """Test getting collection."""
        mock_collection = MagicMock()
        self.mock_client.get_or_create_collection.return_value = mock_collection

        result = self.store.get_collection("test_collection")
        assert result == mock_collection

    def test_get_collection_config(self):
        """Test getting collection config by type."""
        config = self.store.get_collection_config(CollectionType.SEMANTIC_CACHE)
        assert config.name == "semantic_cache"

    @pytest.mark.asyncio
    async def test_add_documents(self):
        """Test adding documents."""
        mock_collection = MagicMock()
        self.store.get_collection = MagicMock(return_value=mock_collection)

        await self.store.add_documents(
            collection_name="test",
            ids=["1", "2"],
            documents=["doc1", "doc2"],
            embeddings=[[0.1, 0.2], [0.3, 0.4]],
            metadatas=[{"a": 1}, {"b": 2}],
        )

        mock_collection.add.assert_called_once_with(
            ids=["1", "2"],
            documents=["doc1", "doc2"],
            embeddings=[[0.1, 0.2], [0.3, 0.4]],
            metadatas=[{"a": 1}, {"b": 2}],
        )

    @pytest.mark.asyncio
    async def test_add_documents_no_collection(self):
        """Test adding documents when collection unavailable."""
        self.store.get_collection = MagicMock(return_value=None)

        await self.store.add_documents("test", ["1"], ["doc"], [[0.1]])
        # Should not raise, just log warning

    @pytest.mark.asyncio
    async def test_search(self):
        """Test vector similarity search."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["1", "2"]],
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"a": 1}, {"b": 2}]],
            "distances": [[0.1, 0.2]],
        }
        self.store.get_collection = MagicMock(return_value=mock_collection)

        results = await self.store.search("test", [0.1, 0.2], top_k=2)

        assert len(results) == 2
        assert results[0]["id"] == "1"
        assert results[0]["content"] == "doc1"
        assert results[0]["distance"] == 0.1

    @pytest.mark.asyncio
    async def test_search_no_results(self):
        """Test search with no results."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        self.store.get_collection = MagicMock(return_value=mock_collection)

        results = await self.store.search("test", [0.1, 0.2])
        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_score(self):
        """Test search with score threshold."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "ids": [["1", "2"]],
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"a": 1}, {"b": 2}]],
            "distances": [[0.1, 0.5]],  # similarity: 0.9, 0.5
        }
        self.store.get_collection = MagicMock(return_value=mock_collection)

        results = await self.store.search_with_score("test", [0.1, 0.2], min_score=0.7)

        assert len(results) == 1
        assert results[0]["similarity"] == 0.9

    @pytest.mark.asyncio
    async def test_delete_by_id(self):
        """Test deleting documents by ID."""
        mock_collection = MagicMock()
        self.store.get_collection = MagicMock(return_value=mock_collection)

        await self.store.delete_by_id("test", ["1", "2"])
        mock_collection.delete.assert_called_once_with(ids=["1", "2"])

    @pytest.mark.asyncio
    async def test_clear_collection(self):
        """Test clearing collection."""
        self.mock_client.delete_collection = MagicMock()

        await self.store.clear_collection("test")

        self.mock_client.delete_collection.assert_called_once_with(name="test")
        assert "test" not in self.store._collections
        assert "test" not in self.store._initialized_collections

    @pytest.mark.asyncio
    async def test_get_collection_stats(self):
        """Test getting collection statistics."""
        mock_collection = MagicMock()
        mock_collection.count.return_value = 100
        self.store.get_collection = MagicMock(return_value=mock_collection)

        stats = await self.store.get_collection_stats("test")

        assert stats["count"] == 100
        assert stats["name"] == "test"

    def test_list_collections(self):
        """Test listing initialized collections."""
        self.store._initialized_collections = {"col1", "col2"}

        result = self.store.list_collections()
        assert set(result) == {"col1", "col2"}

    def test_build_bm25_index(self):
        """Test BM25 index building."""
        with patch("src.services.vector_store.HAS_BM25", True):
            with patch("src.services.vector_store.BM25Okapi") as mock_bm25:
                mock_instance = MagicMock()
                mock_bm25.return_value = mock_instance

                self.store._build_bm25_index("test", ["doc1", "doc2"], ["1", "2"])

                assert "test" in self.store._bm25_indexes
                mock_bm25.assert_called_once()

    def test_build_bm25_index_unavailable(self):
        """Test BM25 index building when BM25 unavailable."""
        with patch("src.services.vector_store.HAS_BM25", False):
            self.store._build_bm25_index("test", ["doc1"], ["1"])
            assert "test" not in self.store._bm25_indexes

    @pytest.mark.asyncio
    async def test_add_documents_with_bm25_new(self):
        """Test adding documents with BM25 for new collection."""
        self.store.add_documents = AsyncMock()
        self.store._build_bm25_index = MagicMock()

        with patch("src.services.vector_store.HAS_BM25", True):
            await self.store.add_documents_with_bm25(
                "test", ["1"], ["doc"], [[0.1]]
            )

        self.store._build_bm25_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_documents_with_bm25_existing(self):
        """Test adding documents with BM25 for existing collection."""
        self.store.add_documents = AsyncMock()
        self.store._build_bm25_index = MagicMock()
        self.store._bm25_indexes["test"] = {"documents": ["old"], "doc_ids": ["0"]}

        with patch("src.services.vector_store.HAS_BM25", True):
            await self.store.add_documents_with_bm25(
                "test", ["1"], ["doc"], [[0.1]]
            )

        self.store._build_bm25_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_hybrid_search(self):
        """Test hybrid vector + BM25 search."""
        # Mock vector search
        self.store.search_with_score = AsyncMock(return_value=[
            {"id": "1", "content": "doc1", "similarity": 0.9, "metadata": {}},
        ])

        # Mock BM25 index
        mock_bm25 = MagicMock()
        mock_bm25.get_scores.return_value = [10.0, 5.0]
        self.store._bm25_indexes["test"] = {
            "bm25": mock_bm25,
            "doc_ids": ["1", "2"],
            "corpus_tokens": [["doc1"], ["doc2"]],
            "documents": ["doc1", "doc2"],
        }

        with patch("src.services.vector_store.HAS_BM25", True):
            results = await self.store.hybrid_search(
                "test", "query", [0.1, 0.2], alpha=0.5
            )

        assert len(results) > 0
        assert "combined_score" in results[0]

    @pytest.mark.asyncio
    async def test_hybrid_search_no_bm25(self):
        """Test hybrid search when BM25 unavailable."""
        self.store.search_with_score = AsyncMock(return_value=[
            {"id": "1", "content": "doc1", "similarity": 0.9, "metadata": {}},
        ])

        with patch("src.services.vector_store.HAS_BM25", False):
            results = await self.store.hybrid_search("test", "query", [0.1, 0.2], alpha=0.5)

        assert len(results) == 1
        # When BM25 is unavailable, the combined score uses alpha=0.5 default
        assert results[0]["combined_score"] == 0.45  # 0.5 * 0.9

    def test_rebuild_bm25_index(self):
        """Test BM25 index rebuild."""
        mock_collection = MagicMock()
        mock_collection.get.return_value = {
            "ids": ["1", "2"],
            "documents": ["doc1", "doc2"],
            "metadatas": [{}, {}],
        }
        self.store.get_collection = MagicMock(return_value=mock_collection)
        self.store._build_bm25_index = MagicMock()

        with patch("src.services.vector_store.HAS_BM25", True):
            self.store.rebuild_bm25_index("test")

        self.store._build_bm25_index.assert_called_once_with("test", ["doc1", "doc2"], ["1", "2"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])