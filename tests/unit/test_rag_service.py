"""GraphRAG 検索・Reranking サービスの単体テスト."""
from unittest.mock import patch, MagicMock
import pytest
import time

from src.services.rag_service import GraphRAGService


def test_rerank_graph_neighbors():
    """Reranking: ユーザープロンプトに最も意味的に近いグラフノードが上位に再評価される."""
    service = GraphRAGService()
    neighbors = [
        {"name": "宿屋の主人", "relation_type": "KNOWS", "properties": {"description": "平凡な宿屋"}},
        {"name": "魔王軍幹部", "relation_type": "ENEMY_OF", "properties": {"description": "闇の魔法の使い手"}},
        {"name": "聖剣の鞘", "relation_type": "ITEM", "properties": {"description": "光の加護を持つ"}},
    ]

    with patch("src.services.rag_service.embedding_service") as mock_emb:
        # プロンプト「魔王軍との戦い」に対して、魔王軍幹部が一番類似度高くなるようにベクトルをモック
        def fake_embedding(text: str):
            if "魔王" in text:
                return [1.0, 0.0, 0.0]
            elif "聖剣" in text:
                return [0.0, 1.0, 0.0]
            else:
                return [0.0, 0.0, 1.0]

        mock_emb.get_embedding.side_effect = fake_embedding

        ranked = service.rerank_graph_neighbors(
            neighbors=neighbors,
            current_prompt="魔王軍の幹部と戦闘を開始するシーン",
            top_k=2,
        )

        assert len(ranked) == 2
        # 最上位が「魔王軍幹部」になっていること
        assert ranked[0]["name"] == "魔王軍幹部"


def test_cosine_similarity():
    """コサイン類似度の計算精度テスト."""
    service = GraphRAGService()
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [1.0, 0.0, 0.0]
    vec_c = [0.0, 1.0, 0.0]

    assert abs(service._cosine_similarity(vec_a, vec_b) - 1.0) < 1e-5
    assert abs(service._cosine_similarity(vec_a, vec_c) - 0.0) < 1e-5
    assert service._cosine_similarity([], []) == 0.0


# Test GraphRAGService initialization and basic functionality
def test_graph_rag_service_init():
    """Test GraphRAGService initialization."""
    service = GraphRAGService()
    
    assert service._token_budget == 3000
    assert service._enable_cache is True
    assert service._cache == {}
    assert service._last_call_stats == {}


def test_graph_rag_service_init_custom_params():
    """Test GraphRAGService initialization with custom parameters."""
    service = GraphRAGService(
        token_budget=5000,
        enable_cache=False
    )
    
    assert service._token_budget == 5000
    assert service._enable_cache is False
    assert service._cache == {}
    assert service._last_call_stats == {}


def test_graph_rag_service_get_reranker():
    """Test get_reranker method."""
    service = GraphRAGService()
    
    # Initially _reranker is None
    assert service._reranker is None
    
    # Call get_reranker - should create a reranker
    with patch("src.services.reranker.build_default_reranker") as mock_build:
        mock_reranker = MagicMock()
        mock_build.return_value = mock_reranker
        
        reranker = service.get_reranker()
        
        assert reranker == mock_reranker
        assert service._reranker == mock_reranker
        mock_build.assert_called_once()


def test_graph_rag_service_get_last_stats():
    """Test get_last_stats method."""
    service = GraphRAGService()
    
    # Initially empty
    stats = service.get_last_stats()
    assert stats == {}
    
    # Set some stats
    test_stats = {"backend": "test", "hits": 10}
    service._last_call_stats = test_stats
    
    # Should return a copy
    returned_stats = service.get_last_stats()
    assert returned_stats == test_stats
    # Modifying returned stats should not affect internal stats
    returned_stats["modified"] = True
    assert "modified" not in service._last_call_stats


def test_graph_rag_service_get_cache_key():
    """Test _get_cache_key method."""
    service = GraphRAGService()
    
    key = service._get_cache_key("arg1", "arg2", "arg3")
    assert isinstance(key, str)
    assert len(key) == 32  # MD5 hash length
    
    # Same inputs should produce same key
    key2 = service._get_cache_key("arg1", "arg2", "arg3")
    assert key == key2
    
    # Different inputs should produce different key
    key3 = service._get_cache_key("arg1", "arg2", "different")
    assert key != key3


def test_graph_rag_service_get_cached():
    """Test _get_cached method."""
    from src.services.rag_service import RagContext
    import time
    
    service = GraphRAGService()
    
    # Test when caching is disabled
    service._enable_cache = False
    assert service._get_cached("key") is None
    
    # Test when key doesn't exist
    service._enable_cache = True
    assert service._get_cached("nonexistent") is None
    
    # Test when key exists but expired
    service._cache["expired_key"] = (MagicMock(), time.time() - 400)  # Expired (TTL=300)
    assert service._get_cached("expired_key") is None
    # Expired key should be removed
    assert "expired_key" not in service._cache
    
    # Test when key exists and is valid
    context = RagContext(
        graph_context="graph",
        vector_context="vector",
        fulltext_context="fulltext",
        stats={},
        token_estimate=100
    )
    service._cache["valid_key"] = (context, time.time() - 100)  # Valid (not expired)
    result = service._get_cached("valid_key")
    assert result == context


def test_graph_rag_service_set_cache():
    """Test _set_cache method."""
    from src.services.rag_service import RagContext
    import time
    
    service = GraphRAGService()
    service._enable_cache = True
    
    context = RagContext(
        graph_context="graph",
        vector_context="vector",
        fulltext_context="fulltext",
        stats={},
        token_estimate=100
    )
    
    service._set_cache("test_key", context)
    
    assert "test_key" in service._cache
    cached_context, timestamp = service._cache["test_key"]
    assert cached_context == context
    # Timestamp should be recent
    assert abs(time.time() - timestamp) < 1


def test_graph_rag_service_clear_cache():
    """Test clear_cache method."""
    service = GraphRAGService()
    
    # Add some items to cache
    service._cache["key1"] = (MagicMock(), 1000)
    service._cache["key2"] = (MagicMock(), 2000)
    service._last_call_stats = {"stat": "value"}
    
    service.clear_cache()
    
    assert service._cache == {}
    # _last_call_stats should not be affected by clear_cache
    assert service._last_call_stats == {"stat": "value"}


def test_graph_rag_service_estimate_tokens():
    """Test _estimate_tokens method."""
    service = GraphRAGService()
    
    # Empty string
    assert service._estimate_tokens("") == 0
    
    # ASCII text
    assert service._estimate_tokens("hello world") == int(0 / 1.5 + 2 * 1.3)  # 0 Japanese chars, 2 English words
    
    # Japanese text
    japanese_text = "こんにちは"
    # 5 Japanese chars, 1 English word (split() returns ['こんにちは'] which has length 1)
    expected = int(5 / 1.5 + 1 * 1.3)
    assert service._estimate_tokens(japanese_text) == expected
    
    # Mixed text
    mixed_text = "こんにちは world"
    # 5 Japanese chars, 2 English words
    expected = int(5 / 1.5 + 2 * 1.3)
    assert service._estimate_tokens(mixed_text) == expected


def test_graph_rag_service_truncate_to_budget():
    """Test _truncate_to_budget method."""
    service = GraphRAGService()
    
    # Test with empty list
    assert service._truncate_to_budget([], 100) == []
    
    # Test with items that fit within budget
    short_texts = ["短", "短い"]  # Short Japanese texts
    result = service._truncate_to_budget(short_texts, 100)
    assert result == short_texts
    
    # Test with items that exceed budget
    # Each Japanese char takes ~0.67 tokens (1/1.5)
    # So 100 Japanese chars would be ~150 tokens
    long_japanese_text = "あ" * 150  # Should exceed budget of 100
    short_japanese_text = "あ" * 50   # Should fit within budget
    
    result = service._truncate_to_budget([long_japanese_text, short_japanese_text], 100)
    # First item should be truncated, second item should be included if it fits
    assert len(result) >= 1
    # The first item should be truncated with "..."
    if len(result) > 0:
        assert result[0].endswith("...")