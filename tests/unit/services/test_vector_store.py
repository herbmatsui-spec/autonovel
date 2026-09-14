import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.vector_store import ChromaVectorStore, ChromaClientProvider, InMemoryFallbackStore

@pytest.mark.asyncio
async def test_vector_store_add_and_search():
    mock_client = MagicMock()
    mock_col = MagicMock()
    mock_col.query.return_value = {
        "ids": [["id1"]],
        "documents": [["勇者が現れた"]],
        "metadatas": [[{"chapter": 1}]],
        "distances": [[0.12]]
    }
    mock_client.get_or_create_collection.return_value = mock_col
    
    mock_provider = MagicMock(spec=ChromaClientProvider)
    mock_provider.get_client.return_value = mock_client
    
    store = ChromaVectorStore(client_provider=mock_provider)
    res = await store.search("semantic_cache", [0.1, 0.2], top_k=1)
    
    assert len(res) == 1
    assert res[0]["content"] == "勇者が現れた"

@pytest.mark.asyncio
async def test_in_memory_fallback_store():
    store = InMemoryFallbackStore(max_items_per_collection=10)
    await store.add_documents(
        collection_name="test_col",
        ids=["1"],
        documents=["テスト文書"],
        embeddings=[[1.0, 0.0]],
        metadatas=[{"genre": "fantasy"}]
    )
    res = await store.search("test_col", [1.0, 0.0], top_k=1)
    assert len(res) == 1
    assert res[0]["content"] == "テスト文書"
    assert res[0]["similarity"] == pytest.approx(1.0)
