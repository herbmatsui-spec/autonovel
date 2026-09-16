from __future__ import annotations

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import os

from src.services.vector_store import (
    get_default_store,
    InMemoryFallbackStore,
    PgVectorStore,
    ChromaVectorStore,
    ChromaClientProvider,
    CollectionType,
    CollectionConfig,
    DEFAULT_COLLECTIONS,
)

# ==============================================================================
# 1. InMemoryFallbackStore Tests
# ==============================================================================

class TestInMemoryFallbackStore:
    @pytest.fixture
    def store(self):
        return InMemoryFallbackStore(max_items_per_collection=10, enable_graph=True)

    @pytest.mark.asyncio
    async def test_basic_add_and_search(self, store):
        collection = "test_col"
        ids = ["id1", "id2"]
        docs = ["Hello world", "Goodbye moon"]
        embs = [[1.0, 0.0], [0.0, 1.0]]
        metas = [{"tag": "a"}, {"tag": "b"}]

        await store.add_documents(collection, ids, docs, embs, metas)
        
        # Exact match
        res = await store.search(collection, [1.0, 0.0], top_k=1)
        assert len(res) == 1
        assert res[0]["id"] == "id1"
        assert res[0]["similarity"] == 1.0

    @pytest.mark.asyncio
    async def test_metadata_filtering(self, store):
        collection = "filter_col"
        await store.add_documents(
            collection, 
            ["id1", "id2"], 
            ["doc1", "doc2"], 
            [[1.0, 0.0], [0.0, 1.0]], 
            [{"genre": "fantasy"}, {"genre": "school"}]
        )

        # Filter fantasy
        res = await store.search(collection, [0.5, 0.5], where={"genre": "fantasy"})
        assert len(res) == 1
        assert res[0]["id"] == "id1"

        # Filter school
        res = await store.search(collection, [0.5, 0.5], where={"genre": "school"})
        assert len(res) == 1
        assert res[0]["id"] == "id2"

        # Filter none
        res = await store.search(collection, [0.5, 0.5], where={"genre": "sci-fi"})
        assert len(res) == 0

    @pytest.mark.asyncio
    async def test_cosine_zero_division(self, store):
        # Test with zero vectors to ensure no crash
        res = store._cosine([0.0, 0.0], [0.0, 0.0])
        assert res == 0.0
        res = store._cosine([1.0, 0.0], [0.0, 0.0])
        assert res == 0.0

    @pytest.mark.asyncio
    async def test_fifo_ring_buffer(self, store):
        collection = "fifo_col"
        # max_items_per_collection is 10
        ids = [f"id{i}" for i in range(15)]
        docs = [f"doc{i}" for i in range(15)]
        embs = [[0.1] * 2 for _ in range(15)]
        
        await store.add_documents(collection, ids, docs, embs)
        
        # Should only keep the last 10 (id5 to id14)
        bucket = store._data[collection]
        assert len(bucket) == 10
        assert bucket[0][0] == "id5"
        assert bucket[-1][0] == "id14"

    @pytest.mark.asyncio
    async def test_delete_and_clear(self, store):
        collection = "del_col"
        await store.add_documents(collection, ["id1", "id2"], ["d1", "d2"], [[1.0], [0.0]])
        
        await store.delete_by_id(collection, ["id1"])
        res = await store.search(collection, [1.0])
        assert len(res) == 1
        assert res[0]["id"] == "id2"
        
        await store.clear_collection(collection)
        assert collection not in store._data

    @pytest.mark.asyncio
    async def test_graph_neighbors_and_validity(self, store):
        collection = "graph_col"
        # Add documents with entities and relations
        await store.add_documents(
            collection,
            ["id1", "id2", "id3"],
            ["d1", "d2", "d3"],
            [[1.0], [0.0], [0.0]],
            [
                {"entities": ["Hero"], "relations": [{"src": "Hero", "dst": "Sword", "type": "owns"}]},
                {"entities": ["Sword"], "relations": [{"src": "Sword", "dst": "Legend", "type": "part_of"}]},
                {"entities": ["Legend"], "status": "retired"}
            ]
        )

        # BFS neighbors
        neighbors = await store.get_neighbors(collection, "Hero", max_depth=2)
        # Hero -> Sword (depth 1), Sword -> Legend (depth 2)
        ids = [n["entity"] for n in neighbors]
        assert "Sword" in ids
        assert "Legend" in ids

        # Validity check
        validity = await store.check_entity_validity(collection, "Legend")
        assert validity["is_retired"] is True
        assert validity["valid"] is False

        validity_ok = await store.check_entity_validity(collection, "Hero")
        assert validity_ok["valid"] is True

# ==============================================================================
# 2. PgVectorStore Tests (Mocked)
# ==============================================================================

class TestPgVectorStore:
    @pytest.fixture
    def mock_db(self):
        with patch("src.services.vector_store.pgvector.create_async_engine") as mock_engine, \
             patch("src.services.vector_store.pgvector.async_sessionmaker") as mock_sessionmaker_factory:
            
            # session_factory() -> session
            mock_session = AsyncMock()
            # Ensure the session acts as an async context manager
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            
            mock_session_factory = MagicMock()
            mock_session_factory.return_value = mock_session
            mock_sessionmaker_factory.return_value = mock_session_factory
            
            # Mock session.execute().fetchall()
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                ("id1", "content1", {"meta": "val"}, 0.1),
            ]
            mock_session.execute.return_value = mock_result
            
            yield {
                "engine": mock_engine,
                "sessionmaker": mock_sessionmaker_factory,
                "session": mock_session
            }

    @pytest.mark.asyncio
    async def test_pg_ensure_table(self, mock_db):
        store = PgVectorStore(database_url="postgresql://user:pass@localhost/db")
        
        # First call should trigger table creation
        success = await store._ensure_table("test_col")
        assert success is True
        assert "test_col" in store._initialized_tables
        
        # Check if SQL was executed
        calls = [call.args[0] for call in mock_db["session"].execute.call_args_list]
        # Check if any call contains CREATE TABLE
        assert any("CREATE TABLE IF NOT EXISTS vec_test_col" in str(c) for c in calls)

    @pytest.mark.asyncio
    async def test_pg_add_documents_batching(self, mock_db):
        store = PgVectorStore(database_url="postgresql://user:pass@localhost/db")
        
        # Add 150 documents (should trigger 2 batches: 100 + 50)
        ids = [f"id{i}" for i in range(150)]
        docs = [f"doc{i}" for i in range(150)]
        embs = [[0.1]*1536 for _ in range(150)]
        
        await store.add_documents("test_col", ids, docs, embs)
        
        # Verify execute was called for each batch
        # 1 for _ensure_table (if not cached) + 2 for batches
        # But _ensure_table is called inside add_documents
        # Let's count the INSERT statements
        insert_calls = [call for call in mock_db["session"].execute.call_args_list if "INSERT INTO" in str(call.args[0])]
        assert len(insert_calls) == 2

    @pytest.mark.asyncio
    async def test_pg_search_sql_construction(self, mock_db):
        store = PgVectorStore(database_url="postgresql://user:pass@localhost/db")
        
        await store.search("test_col", [0.1]*1536, where={"genre": "fantasy"})
        
        # Check if WHERE clause was correctly added
        last_call = mock_db["session"].execute.call_args
        sql = str(last_call.args[0])
        assert "WHERE metadata->>'genre' = :meta_0" in sql
        assert last_call.args[1]["meta_0"] == "fantasy"

    @pytest.mark.asyncio
    async def test_pg_error_rollback(self, mock_db):
        store = PgVectorStore(database_url="postgresql://user:pass@localhost/db")
        
        # Force an exception during add_documents
        mock_db["session"].execute.side_effect = Exception("DB Error")
        
        with pytest.raises(Exception) as excinfo:
            await store.add_documents("test_col", ["id1"], ["doc1"], [[0.1]*1536])
        
        assert "DB Error" in str(excinfo.value)
        mock_db["session"].rollback.assert_called()

# ==============================================================================
# 3. ChromaVectorStore Tests (Mocked)
# ==============================================================================

class TestChromaVectorStore:
    @pytest.fixture
    def mock_chroma(self):
        mock_provider = MagicMock(spec=ChromaClientProvider)
        mock_client = MagicMock()
        mock_collection = MagicMock()
        
        mock_provider.get_client.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_client.get_collection.return_value = mock_collection
        
        return {
            "provider": mock_provider,
            "client": mock_client,
            "collection": mock_collection
        }

    @pytest.mark.asyncio
    async def test_chroma_batch_add(self, mock_chroma):
        store = ChromaVectorStore(client_provider=mock_chroma["provider"])
        
        # Add 500 documents (should trigger 2 batches: 416 + 84)
        ids = [f"id{i}" for i in range(500)]
        docs = [f"doc{i}" for i in range(500)]
        embs = [[0.1]*1536 for _ in range(500)]
        
        # Manually inject collection to avoid initialization logic
        store._collections["test_col"] = mock_chroma["collection"]
        
        await store.add_documents("test_col", ids, docs, embs)
        
        assert mock_chroma["collection"].add.call_count == 2

    @pytest.mark.asyncio
    async def test_chroma_hybrid_search_logic(self, mock_chroma):
        store = ChromaVectorStore(client_provider=mock_chroma["provider"])
        store._collections["test_col"] = mock_chroma["collection"]
        
        # Mock vector search results
        mock_chroma["collection"].query.return_value = {
            "ids": [["v1"]],
            "documents": [["doc_v1"]],
            "metadatas": [[{"meta": "v1"}]],
            "distances": [[0.1]],
        }
        
        # Mock BM25 index
        store._bm25_indexes["test_col"] = {
            "bm25": MagicMock(),
            "doc_ids": ["b1"],
            "documents": ["doc_b1"],
        }
        # Mock BM25 scores: b1 has high score
        store._bm25_indexes["test_col"]["bm25"].get_scores.return_value = [10.0]
        
        res = await store.hybrid_search(
            "test_col", 
            query_text="test query", 
            query_embedding=[0.1]*1536, 
            top_k=2, 
            alpha=0.5
        )
        
        # Should contain both v1 and b1
        ids = [r["id"] for r in res]
        assert "v1" in ids
        assert "b1" in ids

# ==============================================================================
# 4. get_default_store Tests
# ==============================================================================

class TestGetDefaultStore:
    @patch("src.services.vector_store.InMemoryFallbackStore")
    @patch("src.services.vector_store.ChromaVectorStore")
    @patch("src.services.vector_store.PgVectorStore")
    @patch("os.environ.get")
    @patch("src.backend.config.settings")
    def test_store_selection_modes(self, mock_settings, mock_env, mock_pg, mock_chroma, mock_inmem):
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost/db"
        # Mode: pgvector
        mock_settings.AUTONOVEL_RAG_MODE = "pgvector"
        mock_env.return_value = "pgvector"
        
        # Mock HAS_PGVECTOR = True
        with patch("src.services.vector_store.HAS_PGVECTOR", True):
            get_default_store()
            mock_pg.assert_called()
        
        mock_pg.reset_mock()
        
        # Mode: chroma
        mock_settings.AUTONOVEL_RAG_MODE = "chroma"
        mock_env.return_value = "chroma"
        with patch("src.services.vector_store.HAS_CHROMA", True):
            get_default_store()
            mock_chroma.assert_called()
        
        mock_chroma.reset_mock()
        
        # Mode: memory
        mock_settings.AUTONOVEL_RAG_MODE = "memory"
        mock_env.return_value = "memory"
        get_default_store()
        mock_inmem.assert_called()

    @patch("os.environ.get")
    @patch("src.backend.config.settings")
    def test_auto_fallback_priority(self, mock_settings, mock_env):
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost/db"
        mock_settings.AUTONOVEL_RAG_MODE = "auto"
        mock_env.return_value = "auto"
        
        # Priority: PgVector > Chroma > Memory
        
        # Case 1: PgVector available
        with patch("src.services.vector_store.HAS_PGVECTOR", True), \
             patch("src.services.vector_store.PgVectorStore") as mock_pg:
            get_default_store()
            mock_pg.assert_called()
            
        # Case 2: PgVector unavailable, Chroma available
        with patch("src.services.vector_store.HAS_PGVECTOR", False), \
             patch("src.services.vector_store.HAS_CHROMA", True), \
             patch("src.services.vector_store.ChromaVectorStore") as mock_chroma:
            get_default_store()
            mock_chroma.assert_called()
            
        # Case 3: Both unavailable -> Memory
        with patch("src.services.vector_store.HAS_PGVECTOR", False), \
             patch("src.services.vector_store.HAS_CHROMA", False), \
             patch("src.services.vector_store.InMemoryFallbackStore") as mock_inmem:
            get_default_store()
            mock_inmem.assert_called()
