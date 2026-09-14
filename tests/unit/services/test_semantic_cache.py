import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.semantic_cache import SemanticCacheManager

@pytest.mark.asyncio
async def test_semantic_cache_hit_and_miss():
    mock_vector_store = AsyncMock()
    mock_client = MagicMock()
    
    mock_embed_res = MagicMock()
    mock_embed_res.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
    mock_client.models.embed_content.return_value = mock_embed_res
    
    cache = SemanticCacheManager(vector_store=mock_vector_store, client=mock_client)
    
    # Hit case (distance 0.10 <= 0.15 for threshold 0.85)
    mock_vector_store.search.return_value = [
        {
            "id": "doc1",
            "content": "生成テキストA",
            "metadata": {"input_length": 5},
            "distance": 0.10
        }
    ]
    hit = await cache.search("プロンプトA似", task_type="generation", threshold=0.85)
    assert hit == "生成テキストA"
    
    # Miss case (distance 0.30 > 0.15 for threshold 0.85)
    mock_vector_store.search.return_value = [
        {
            "id": "doc2",
            "content": "生成テキストB",
            "metadata": {"input_length": 7},
            "distance": 0.30
        }
    ]
    miss = await cache.search("全然違う質問", task_type="generation", threshold=0.85)
    assert miss is None
