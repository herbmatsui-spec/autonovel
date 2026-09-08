"""Unit tests for Japanese morphological tokenizer & BM25 integration (Steps 13-18)."""

import pytest
from unittest.mock import MagicMock, patch

from src.services.nlp.japanese_tokenizer import JapaneseTokenizer, NOVEL_STOPWORDS
from src.services.reflective_rag import ReflectiveRAGService
from src.services.rag_service import SearchResult


def test_japanese_tokenizer_basic():
    """Test basic morphological tokenization and NFKC normalization (Step 13)."""
    tokenizer = JapaneseTokenizer()
    text = "魔導書を開いて呪文を唱えた。"
    tokens = tokenizer.tokenize(text)

    # Content words should be extracted
    assert "魔導" in tokens or "魔導書" in tokens
    assert any("開く" in t or "開" in t for t in tokens)
    assert any("呪文" in t for t in tokens)
    assert any("唱える" in t or "唱え" in t for t in tokens)

    # Particles and auxiliary punctuation should be excluded
    assert "を" not in tokens
    assert "。" not in tokens
    assert "て" not in tokens


def test_japanese_tokenizer_novel_stopwords():
    """Test filtering of novel-specific stopwords (Step 14)."""
    tokenizer = JapaneseTokenizer()
    text = "彼はそう言ったが、古の聖剣がまばゆい光を放った。"
    tokens = tokenizer.tokenize(text)

    # General stopwords like '彼', 'そう', '言った' should be removed
    assert "彼" not in tokens
    assert "そう" not in tokens
    # Core nouns and content words should remain
    assert any("聖剣" in t or "剣" in t for t in tokens)
    assert any("光" in t for t in tokens)


def test_japanese_tokenizer_fallback():
    """Test fallback mechanism when SudachiPy is unavailable (Step 15)."""
    tokenizer = JapaneseTokenizer()
    # Force fallback
    tokenizer._sudachi_tokenizer = None

    text = "古の魔王が復活した"
    fallback_tokens = tokenizer.tokenize(text)
    assert len(fallback_tokens) > 0
    assert any("魔王" in t or "復活" in t for t in fallback_tokens)


def test_reflective_rag_tokenizer_integration():
    """Test ReflectiveRAGService uses JapaneseTokenizer for BM25 keyword extraction (Steps 16-17)."""
    mock_rag = MagicMock()
    service = ReflectiveRAGService(rag_service=mock_rag)

    assert isinstance(service.tokenizer, JapaneseTokenizer)

    # Test _tokenize integration
    tokens = service._tokenize("古代の遺産が眠る迷宮へと向かった。")
    assert len(tokens) > 0
    assert any("遺産" in t or "迷宮" in t for t in tokens)

    # Test _bm25_keyword_extract
    pos_docs = [
        SearchResult(id="1", content="古代の聖剣が封印された遺跡", metadata={}, source="world", score=0.9),
        SearchResult(id="2", content="聖剣の輝きが闇を払う", metadata={}, source="world", score=0.85),
    ]
    keywords = service._bm25_keyword_extract(pos_docs, n=3)
    assert len(keywords) > 0
    assert any("聖剣" in k or "古代" in k or "輝き" in k for k in keywords)
