from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.vector_store import (
    ChromaClientProvider,
    ChromaVectorStore,
    CollectionConfig,
    CollectionType,
    DEFAULT_COLLECTIONS,
)


def test_collection_types_and_defaults():
    assert CollectionType.SEMANTIC_CACHE.value == "semantic_cache"
    assert CollectionType.STYLE_MEMORY.value == "style_memory"
    assert CollectionType.WORLD_MEMORY.value == "world_memory"
    assert CollectionType.CHARACTER_MEMORY.value == "character_memory"
    assert CollectionType.NARRATIVE_MEMORY.value == "narrative_memory"
    assert CollectionType.EPISODE_MEMORY.value == "episode_memory"

    assert len(DEFAULT_COLLECTIONS) == 6
    cfg = DEFAULT_COLLECTIONS[CollectionType.SEMANTIC_CACHE]
    assert cfg.name == "semantic_cache"
    meta = cfg.get_metadata()
    assert meta["hnsw:space"] == "cosine"
    assert "description" in meta


def test_chroma_client_provider_cache_and_close():
    provider = ChromaClientProvider(db_path="./test_chroma_db")
    mock_client = MagicMock()
    provider._client = mock_client

    assert provider.get_client() is mock_client
    provider.close()
    assert provider._client is None


def test_chroma_vector_store_initialization():
    mock_provider = MagicMock(spec=ChromaClientProvider)
    mock_client = MagicMock()
    mock_provider.get_client.return_value = mock_client

    store = ChromaVectorStore(client_provider=mock_provider)
    assert store.client is mock_client

    mock_collection = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection

    status = store.initialize_collections([CollectionType.SEMANTIC_CACHE])
    assert status.get("semantic_cache") is True
    assert "semantic_cache" in store._collections


@pytest.mark.asyncio
async def test_chroma_vector_store_operations():
    mock_provider = MagicMock(spec=ChromaClientProvider)
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection
    mock_provider.get_client.return_value = mock_client

    store = ChromaVectorStore(client_provider=mock_provider)
    store._collections["test_col"] = mock_collection

    # add_documents
    await store.add_documents(
        collection_name="test_col",
        ids=["id1"],
        documents=["doc1"],
        embeddings=[[0.1, 0.2]],
        metadatas=[{"tag": "test"}],
    )
    mock_collection.add.assert_called_once()

    # search
    mock_collection.query.return_value = {
        "ids": [["id1"]],
        "documents": [["doc1"]],
        "metadatas": [[{"tag": "test"}]],
        "distances": [[0.05]],
    }
    results = await store.search(
        collection_name="test_col",
        query_embedding=[0.1, 0.2],
        top_k=1,
    )
    assert len(results) == 1
    assert results[0]["id"] == "id1"

    # search_with_score
    results_score = await store.search_with_score(
        collection_name="test_col",
        query_embedding=[0.1, 0.2],
        top_k=1,
        min_score=0.0,
    )
    assert len(results_score) == 1

    # delete_by_id
    await store.delete_by_id("test_col", ["id1"])
    mock_collection.delete.assert_called_once_with(ids=["id1"])

    # clear_collection
    await store.clear_collection("test_col")
    mock_client.delete_collection.assert_called_once_with(name="test_col")
