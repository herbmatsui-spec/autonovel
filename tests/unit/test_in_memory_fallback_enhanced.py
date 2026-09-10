import pytest
from src.services.vector_store.in_memory import InMemoryFallbackStore

@pytest.mark.asyncio
async def test_hybrid_search_bm25_rrf():
    store = InMemoryFallbackStore(max_items_per_collection=100, enable_graph=True)
    await store.add_documents(
        "test_col",
        ids=["1", "2", "3"],
        documents=[
            "吾輩は猫である。名前はまだ無い。",
            "吾輩は犬である。名前はポチ。",
            "今日は良い天気だ。",
        ],
        embeddings=[[0.1]*10, [0.2]*10, [0.9]*10],
        metadatas=[{"entities": ["吾輩"]}, {"entities": ["吾輩", "ポチ"]}, {}],
    )
    # クエリ「猫」→ BM25 で doc 1 がヒット、ベクトルでは doc 3 が近い
    results = await store.hybrid_search("test_col", "猫", [0.85]*10, top_k=3, alpha=0.5)
    assert len(results) > 0
    assert "combined_score" in results[0]
    assert "bm25_score" in results[0]
    assert "vector_similarity" in results[0]

@pytest.mark.asyncio
async def test_graph_neighbors_and_validity():
    store = InMemoryFallbackStore(max_items_per_collection=100, enable_graph=True)
    await store.add_documents(
        "world_mem",
        ids=["e1"],
        documents=["キャラAとキャラBは友達"],
        embeddings=[[0.5]*10],
        metadatas=[{
            "entities": ["キャラA", "キャラB"],
            "relations": [{"src": "キャラA", "dst": "キャラB", "type": "friend"}],
        }],
    )
    nbrs = await store.get_neighbors("world_mem", "キャラA", max_depth=2)
    assert any(n["entity"] == "キャラB" for n in nbrs)

    validity = await store.check_entity_validity("world_mem", "キャラA")
    assert validity["valid"] is True
    assert validity["status"] == "active"