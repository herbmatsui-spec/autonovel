from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.semantic_cache import SemanticCacheManager


@pytest.mark.skip(reason="container fixture が未実装のためスキップ")
@pytest.mark.asyncio
async def test_semantic_cache_multi_layer_hit(container):
    """
    セマンティックキャッシュの多階層ヒット (L1 -> L2-B -> L2-A) を検証
    """
    # Mock setup
    mock_vector_store = MagicMock()
    mock_vector_store.search = AsyncMock(return_value=[])
    mock_vector_store.add_documents = AsyncMock()
    mock_vector_store.get_collection = MagicMock()

    mock_client = MagicMock()
    # Mock Embedding API response
    mock_embedding_res = MagicMock()
    mock_embedding_res.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
    mock_client.models.embed_content = MagicMock(return_value=mock_embedding_res)

    cache = SemanticCacheManager(vector_store=mock_vector_store, client=mock_client)

    prompt = "Test prompt for caching"
    task = "test_task"
    response = "Test response"

    # 1. Initial Add (Populate caches)
    await cache.add(prompt, response, task)

    # --- Test L1 Hit ---
    res1 = await cache.search(prompt, task)
    assert res1 == response
    # L1 hit 時は Embedding API が呼ばれない
    assert mock_client.models.embed_content.call_count == 1

    # --- Test L2-B Hit ---
    cache._l1_cache.clear()

    # L1 miss -> L2-B hit: embed_content should NOT be called again.
    await cache.search(prompt, task)
    assert mock_client.models.embed_content.call_count == 1

    # --- Test L2-A (Semantic) Hit ---
    cache._l1_cache.clear()
    cache._l2_embedding_cache.clear()

    # Mock ChromaDB to return a hit
    mock_vector_store.search.return_value = [{
        "id": "doc1",
        "distance": 0.01,
        "content": response,
        "metadata": {"task_type": task, "genre": "general", "input_length": len(prompt)}
    }]

    res3 = await cache.search(prompt, task)
    assert res3 == response
    # L2-B missのため Embedding API が呼ばれる
    assert mock_client.models.embed_content.call_count == 2

@pytest.mark.skip(reason="container fixture が未実装のためスキップ")
@pytest.mark.asyncio
async def test_semantic_cache_eviction(container):
    """
    キャッシュのエビクション（LRU削除）を検証する。
    """
    mock_vector_store = MagicMock()
    mock_vector_store.get_collection = MagicMock()

    mock_collection = MagicMock()
    mock_collection.get.return_value = {
        "ids": [f"id_{i}" for i in range(1100)],
        "metadatas": [{"created_at": "2023-01-01T00:00:00"} for _ in range(1100)]
    }
    mock_vector_store.get_collection.return_value = mock_collection
    mock_vector_store.delete_by_id = AsyncMock()

    cache = SemanticCacheManager(vector_store=mock_vector_store, client=MagicMock())

    await cache.evict_if_needed(max_items=1000)

    assert mock_vector_store.delete_by_id.called
    args, _ = mock_vector_store.delete_by_id.call_args
    assert len(args[1]) == 100
