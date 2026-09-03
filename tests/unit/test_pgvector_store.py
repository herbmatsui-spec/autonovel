"""Unit tests for PgVectorStore."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.vector_store import PgVectorStore, HAS_PGVECTOR


@pytest.mark.skipif(not HAS_PGVECTOR, reason="pgvector not installed")
class TestPgVectorStore:
    """Tests for PgVectorStore."""

    def test_init(self):
        """Test initialization."""
        with patch("src.services.vector_store.create_async_engine") as mock_engine, \
             patch("src.services.vector_store.async_sessionmaker") as mock_session:
            store = PgVectorStore(
                database_url="postgresql+asyncpg://user:pass@localhost/db",
                dimension=768,
                pool_size=5,
                max_overflow=10,
            )
            assert store.database_url == "postgresql+asyncpg://user:pass@localhost/db"
            assert store.dimension == 768
            mock_engine.assert_called_once()
            mock_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_table(self):
        """Test _ensure_table creates table and index."""
        with patch("src.services.vector_store.create_async_engine"), \
             patch("src.services.vector_store.async_sessionmaker"):
            store = PgVectorStore(database_url="postgresql+asyncpg://")
            mock_session = AsyncMock()
            store._session = MagicMock(return_value=mock_session)
            # Mock the async context manager
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None

            result = await store._ensure_table("test_coll")
            assert result is True
            # Ensure CREATE EXTENSION vector was called
            called_args = [call.args[0].text for call in mock_session.execute.call_args_list]
            assert any("CREATE EXTENSION IF NOT EXISTS vector;" in sql for sql in called_args)
            # Ensure table creation SQL executed
            assert any("CREATE TABLE IF NOT EXISTS vec_test_coll" in sql for sql in called_args)
            # Ensure index creation
            assert any("CREATE INDEX IF NOT EXISTS idx_vec_test_coll_embedding_hnsw" in sql for sql in called_args)

    @pytest.mark.asyncio
    async def test_add_documents(self):
        """Test add_documents inserts data."""
        with patch("src.services.vector_store.create_async_engine"), \
             patch("src.services.vector_store.async_sessionmaker"):
            store = PgVectorStore(database_url="postgresql+asyncpg://")
            mock_session = AsyncMock()
            store._session = MagicMock(return_value=mock_session)
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            # Mock _ensure_table to do nothing
            store._ensure_table = AsyncMock(return_value=True)

            await store.add_documents(
                collection_name="test",
                ids=["1", "2"],
                documents=["doc1", "doc2"],
                embeddings=[[0.1, 0.2], [0.3, 0.4]],
                metadatas=[{"a": 1}, {"b": 2}],
            )
            # Ensure execute called with UPSERT
            assert mock_session.execute.call_count >= 1
            # Commit called
            mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_search(self):
        """Test search returns results."""
        with patch("src.services.vector_store.create_async_engine"), \
             patch("src.services.vector_store.async_sessionmaker"):
            store = PgVectorStore(database_url="postgresql+asyncpg://")
            mock_session = AsyncMock()
            store._session = MagicMock(return_value=mock_session)
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            # Mock _ensure_table to do nothing
            store._ensure_table = AsyncMock(return_value=True)
            # Mock execute to return fake rows
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                ("id1", "content1", {"meta": "val"}, 0.1)
            ]
            mock_session.execute.return_value = mock_result

            results = await store.search("test", [0.1, 0.2], top_k=1)
            assert len(results) == 1
            assert results[0]["id"] == "id1"
            assert results[0]["content"] == "content1"
            assert results[0]["metadata"] == {"meta": "val"}
            # distance and similarity should be present
            assert "distance" in results[0]
            assert "similarity" in results[0]

    @pytest.mark.asyncio
    async def test_search_with_score(self):
        """Test search_with_score filters by min_score."""
        with patch("src.services.vector_store.create_async_engine"), \
             patch("src.services.vector_store.async_sessionmaker"):
            store = PgVectorStore(database_url="postgresql+asyncpg://")
            mock_session = AsyncMock()
            store._session = MagicMock(return_value=mock_session)
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            store._ensure_table = AsyncMock(return_value=True)
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                ("id1", "content1", {}, 0.2),  # distance 0.2 => similarity 0.8
                ("id2", "content2", {}, 0.5),  # distance 0.5 => similarity 0.5
            ]
            mock_session.execute.return_value = mock_result

            results = await store.search_with_score("test", [0.1, 0.2], top_k=2, min_score=0.6)
            # Only first result with similarity 0.8 >= 0.6
            assert len(results) == 1
            assert results[0]["id"] == "id1"
            assert results[0]["similarity"] == 0.8

    @pytest.mark.asyncio
    async def test_delete_by_id(self):
        """Test delete_by_id removes rows."""
        with patch("src.services.vector_store.create_async_engine"), \
             patch("src.services.vector_store.async_sessionmaker"):
            store = PgVectorStore(database_url="postgresql+asyncpg://")
            mock_session = AsyncMock()
            store._session = MagicMock(return_value=mock_session)
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            store._ensure_table = AsyncMock(return_value=True)

            await store.delete_by_id("test", ["id1", "id2"])
            # Ensure execute called with DELETE
            assert mock_session.execute.call_count >= 1
            mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_clear_collection(self):
        """Test clear_collection truncates table."""
        with patch("src.services.vector_store.create_async_engine"), \
             patch("src.services.vector_store.async_sessionmaker"):
            store = PgVectorStore(database_url="postgresql+asyncpg://")
            mock_session = AsyncMock()
            store._session = MagicMock(return_value=mock_session)
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            store._ensure_table = AsyncMock(return_value=True)

            await store.clear_collection("test")
            # Ensure execute called with TRUNCATE
            assert mock_session.execute.call_count >= 1
            mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_hybrid_search(self):
        """Test hybrid_search combines vector and text results."""
        with patch("src.services.vector_store.create_async_engine"), \
             patch("src.services.vector_store.async_sessionmaker"):
            store = PgVectorStore(database_url="postgresql+asyncpg://")
            mock_session = AsyncMock()
            store._session = MagicMock(return_value=mock_session)
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            store._ensure_table = AsyncMock(return_value=True)
            # Mock search_with_score to return vector results
            store.search_with_score = AsyncMock(return_value=[
                {"id": "1", "content": "vec1", "similarity": 0.9, "metadata": {}},
                {"id": "2", "content": "vec2", "similarity": 0.7, "metadata": {}},
            ])
            # Mock the text search execute
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                ("2", "text2", {}, 0.8),  # id 2 with rank 0.8
                ("3", "text3", {}, 0.5),  # id 3 with rank 0.5
            ]
            mock_session.execute.return_value = mock_result

            results = await store.hybrid_search(
                collection_name="test",
                query_text="query",
                query_embedding=[0.1, 0.2],
                top_k=2,
                alpha=0.5,
                min_score=0.0,
            )
            # Should have results fused and sorted by rrf_score
            assert len(results) == 2
            # Check that ids are present
            ids = {r["id"] for r in results}
            assert "1" in ids or "2" in ids or "3" in ids
            # Ensure rrf_score key exists
            assert "rrf_score" in results[0]

