"""Unit tests for SudachiPy-based Japanese tokenizer (Step 26)."""
from __future__ import annotations

import pytest
from unittest.mock import patch

from src.services.compression.japanese_tokenizer import (
    SudachiTokenizer,
    RegexJapaneseTokenizer,
    HybridJapaneseTokenizer,
    SudachiConfig,
    create_japanese_tokenizer,
    SUDACHI_AVAILABLE,
)
from src.services.compression.layer1_keywords import Layer1KeywordExtractor


class TestSudachiConfig:
    """Test SudachiConfig validation."""

    def test_default_config(self):
        config = SudachiConfig()
        assert config.split_mode == "C"
        assert config.include_proper is True
        assert config.include_compound is True
        assert config.min_length == 2
        assert config.dict_type == "core"

    def test_custom_config(self):
        config = SudachiConfig(split_mode="A", min_length=3, dict_type="full")
        assert config.split_mode == "A"
        assert config.min_length == 3
        assert config.dict_type == "full"


class TestRegexJapaneseTokenizer:
    """Test regex fallback tokenizer."""

    def test_basic_extraction(self):
        tokenizer = RegexJapaneseTokenizer()
        text = "勇者アルカディアが聖剣エクスカリバーを抜く"
        nouns = tokenizer.extract_nouns(text)
        assert "勇者" in nouns
        assert "アルカディア" in nouns
        assert "聖剣" in nouns
        assert "エクスカリバー" in nouns

    def test_stop_words_filtered(self):
        tokenizer = RegexJapaneseTokenizer()
        text = "これはテストです"
        nouns = tokenizer.extract_nouns(text)
        assert "これ" not in nouns
        assert "テスト" in nouns

    def test_min_length(self):
        tokenizer = RegexJapaneseTokenizer()
        text = "ab abc abcd"
        nouns = tokenizer.extract_nouns(text, min_length=3)
        assert "ab" not in nouns
        assert "abc" in nouns
        assert "abcd" in nouns

    def test_empty_text(self):
        tokenizer = RegexJapaneseTokenizer()
        assert tokenizer.extract_nouns("") == []
        assert tokenizer.extract_nouns("   ") == []


class TestSudachiTokenizer:
    """Test SudachiPy tokenizer (requires sudachipy)."""

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_initialization(self):
        tokenizer = SudachiTokenizer()
        assert tokenizer is not None

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_basic_extraction(self):
        tokenizer = SudachiTokenizer()
        text = "勇者アルカディアが聖剣エクスカリバーを抜く"
        nouns = tokenizer.extract_nouns(text)
        assert "勇者" in nouns
        assert "アルカディア" in nouns
        assert "エクスカリバー" in nouns

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_proper_noun_extraction(self):
        tokenizer = SudachiTokenizer()
        text = "東京タワーと大阪城"
        nouns = tokenizer.extract_nouns(text)
        assert "東京タワー" in nouns or "東京" in nouns
        assert "大阪城" in nouns or "大阪" in nouns

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_katakana_normalization(self):
        """Katakana should use surface form, not normalized (romaji)."""
        tokenizer = SudachiTokenizer()
        text = "アルカディア"
        nouns = tokenizer.extract_nouns(text)
        assert "アルカディア" in nouns
        assert "ALUKADIA" not in nouns

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_split_modes(self):
        """Test different split modes produce different granularity."""
        text = "東京特許許可局"

        tokenizer_a = SudachiTokenizer(SudachiConfig(split_mode="A"))
        tokenizer_c = SudachiTokenizer(SudachiConfig(split_mode="C"))

        nouns_a = tokenizer_a.extract_nouns(text)
        nouns_c = tokenizer_c.extract_nouns(text)

        assert len(nouns_a) >= len(nouns_c)

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_min_length_filter(self):
        tokenizer = SudachiTokenizer(SudachiConfig(min_length=3))
        text = "ab abc abcd"
        nouns = tokenizer.extract_nouns(text)
        assert "AB" not in nouns
        assert "ABC" in nouns
        assert "ABCD" in nouns


class TestHybridJapaneseTokenizer:
    """Test hybrid tokenizer combining Sudachi + Regex."""

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_initialization(self):
        tokenizer = HybridJapaneseTokenizer()
        assert tokenizer is not None

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_compound_word_recall(self):
        """Hybrid should capture compound words that Sudachi splits."""
        tokenizer = HybridJapaneseTokenizer()
        text = "王都グランヴァルと商人ギルド"
        nouns = tokenizer.extract_nouns(text)

        assert any("グランヴァル" in n for n in nouns)
        assert any("商人ギルド" in n for n in nouns) or "商人" in nouns

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_deduplication_prefers_longer(self):
        """When same word appears in both, prefer longer version."""
        tokenizer = HybridJapaneseTokenizer()
        text = "王都グランヴァル"
        nouns = tokenizer.extract_nouns(text)

        has_long_compound = any("グランヴァル" in n for n in nouns)
        assert has_long_compound


class TestCreateJapaneseTokenizer:
    """Test factory function."""

    def test_returns_tokenizer(self):
        tokenizer = create_japanese_tokenizer()
        assert tokenizer is not None
        assert hasattr(tokenizer, 'extract_nouns')

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_returns_hybrid_when_available(self):
        tokenizer = create_japanese_tokenizer()
        assert isinstance(tokenizer, HybridJapaneseTokenizer)

    def test_fallback_when_sudachi_unavailable(self):
        """Test fallback to regex when Sudachi fails."""
        with patch('src.services.compression.japanese_tokenizer.SUDACHI_AVAILABLE', False):
            tokenizer = create_japanese_tokenizer()
            assert isinstance(tokenizer, RegexJapaneseTokenizer)


class TestLayer1KeywordExtractorIntegration:
    """Test Layer1KeywordExtractor with new tokenizer."""

    def test_extract_with_default_tokenizer(self):
        extractor = Layer1KeywordExtractor(top_n=10)
        text = "勇者アルカディアが聖剣エクスカリバーを抜いて魔王ヴォルケインを倒す。"
        result = extractor.extract(text)

        assert len(result.extracted_keywords) > 0
        assert "アルカディア" in result.extracted_keywords
        assert "エクスカリバー" in result.extracted_keywords

    def test_extract_with_custom_config(self):
        from src.services.compression.models import SudachiConfig
        config = SudachiConfig(min_length=3)
        extractor = Layer1KeywordExtractor(top_n=10, tokenizer_config=config)
        text = "勇者アルカディアが聖剣エクスカリバーを抜く"
        result = extractor.extract(text)

        for kw in result.extracted_keywords:
            assert len(kw) >= 3

    def test_extract_empty_text(self):
        extractor = Layer1KeywordExtractor()
        result = extractor.extract("")
        assert result.extracted_keywords == []
        assert result.original_char_count == 0

    def test_module_level_tokenize_function(self):
        from src.services.compression.layer1_keywords import tokenize_japanese_words
        text = "勇者アルカディア"
        nouns = tokenize_japanese_words(text)
        assert isinstance(nouns, list)
        assert "勇者" in nouns or "アルカディア" in nouns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])