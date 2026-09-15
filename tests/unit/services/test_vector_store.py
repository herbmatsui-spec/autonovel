import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.vector_store import InMemoryFallbackStore

@pytest.mark.asyncio
async def test_vector_store_add_and_search():
    # InMemoryFallbackStore は import 可能であるため、これを利用してテストする
    store = InMemoryFallbackStore()
    
    # テストデータを追加
    await store.add_documents(
        collection_name="test_col",
        ids=["id1"],
        documents=["勇者が現れた"],
        embeddings=[[0.1, 0.2, 0.3]],
        metadatas=[{"chapter": 1}]
    )
    
    # 検索（類似度の計算が正しく行われるか確認）
    res = await store.search(
        collection_name="test_col",
        query_embedding=[0.1, 0.2, 0.3], # 同じベクトル
        top_k=1
    )
    
    assert len(res) == 1
    assert res[0]["content"] == "勇者が現れた"
    assert res[0]["metadata"]["chapter"] == 1
