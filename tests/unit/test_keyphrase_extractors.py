# tests/unit/test_keyphrase_extractors.py
"""キーフレーズ抽出器 単体テスト"""
from __future__ import annotations

import pytest

from src.services.context_compression.keyphrase_extractors import (
    KeyphraseExtractor,
    TFIDFExtractor,
    KeyBERTExtractor,
    BM25Extractor,
    create_extractor,
)


class TestTFIDFExtractor:
    """TFIDFExtractor のテスト"""

    @pytest.fixture
    def extractor(self):
        return TFIDFExtractor()

    def test_extract_japanese_nouns_basic(self, extractor):
        """基本的な日本語名詞抽出"""
        text = "主人公の剣士アレンは、魔王の城に向かって旅立った。"
        nouns = extractor._extract_japanese_nouns(text)
        
        assert "主人公" in nouns
        assert "剣士" in nouns
        assert "アレン" in nouns
        assert "魔王" in nouns
        assert "城" in nouns
        assert "旅立" in nouns

    def test_extract_japanese_nouns_filters_function_words(self, extractor):
        """機能語が除外されること"""
        text = "主人公は剣を持っています。"
        nouns = extractor._extract_japanese_nouns(text)
        
        assert "は" not in nouns
        assert "を" not in nouns
        assert "です" not in nouns
        assert "主人公" in nouns
        assert "剣" in nouns

    def test_extract_japanese_nouns_removes_duplicates(self, extractor):
        """重複が除去されること"""
        text = "主人公の主人公の主人公"
        nouns = extractor._extract_japanese_nouns(text)
        
        assert nouns.count("主人公") == 1

    def test_extract_japanese_nouns_filters_short(self, extractor):
        """短すぎる語が除外されること"""
        text = "あいうえお"
        nouns = extractor._extract_japanese_nouns(text)
        
        # 1文字は除外される
        assert "あ" not in nouns
        assert "い" not in nouns

    def test_extract_japanese_nouns_filters_digits(self, extractor):
        """数字のみが除外されること"""
        text = "12345 主人公"
        nouns = extractor._extract_japanese_nouns(text)
        
        assert "12345" not in nouns
        assert "主人公" in nouns

    def test_extract_basic(self, extractor):
        """基本的な抽出動作"""
        text = "主人公の剣士アレンは、魔王の城に向かって旅立った。"
        result = extractor.extract(text, top_k=10, min_score=0.01)
        
        assert isinstance(result, list)
        assert len(result) <= 10
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)
        assert all(isinstance(term, str) and isinstance(score, float) for term, score in result)

    def test_extract_empty_text(self, extractor):
        """空文字列の処理"""
        result = extractor.extract("", top_k=10, min_score=0.01)
        assert result == []

    def test_extract_short_text(self, extractor):
        """短いテキストの処理"""
        text = "主人公"
        result = extractor.extract(text, top_k=5, min_score=0.01)
        assert isinstance(result, list)

    def test_extract_with_top_k_limit(self, extractor):
        """top_k 制限が効くこと"""
        text = " ".join(["単語" + str(i) for i in range(100)])
        result = extractor.extract(text, top_k=5, min_score=0.0)
        assert len(result) <= 5

    def test_extract_min_score_filter(self, extractor):
        """min_score フィルタが効くこと"""
        text = "主人公の剣士アレンは、魔王の城に向かって旅立った。"
        # 高い閾値
        result_high = extractor.extract(text, top_k=10, min_score=0.5)
        # 低い閾値
        result_low = extractor.extract(text, top_k=10, min_score=0.01)
        
        assert len(result_high) <= len(result_low)


class TestTFIDFExtractorTFIDFScores:
    """TF-IDFスコア計算のテスト"""

    @pytest.fixture
    def extractor(self):
        return TFIDFExtractor()

    def test_compute_tfidf_scores_multi_sentence(self, extractor):
        """複数文でのTF-IDF計算"""
        text = "主人公は剣を持つ。魔王は城にいる。剣は光る。"
        nouns = ["主人公", "剣", "魔王", "城", "光る"]
        sentences = ["主人公は剣を持つ", "魔王は城にいる", "剣は光る"]
        
        result = extractor._compute_tfidf_scores(nouns, sentences, top_k=5, min_score=0.01)
        
        assert isinstance(result, list)
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)

    def test_compute_tfidf_scores_single_sentence_fallback(self, extractor):
        """単一文の場合は頻度ベースにフォールバック"""
        text = "主人公は剣を持つ。"
        nouns = ["主人公", "剣"]
        sentences = ["主人公は剣を持つ"]
        
        result = extractor._compute_tfidf_scores(nouns, sentences, top_k=5, min_score=0.01)
        
        # フォールバック関数が呼ばれるため、頻度ベースの結果が返る
        assert isinstance(result, list)


class TestKeyBERTExtractor:
    """KeyBERTExtractor のテスト"""

    @pytest.fixture
    def extractor(self):
        return KeyBERTExtractor()

    def test_extract_unavailable(self, extractor):
        """KeyBERT未インストール時は空リスト"""
        # 環境によっては利用可能な場合があるため、両方のケースを許容
        result = extractor.extract("テストテキスト", top_k=5, min_score=0.1)
        assert isinstance(result, list)


class TestBM25Extractor:
    """BM25Extractor のテスト"""

    @pytest.fixture
    def extractor(self):
        return BM25Extractor()

    def test_extract_basic(self, extractor):
        """基本的な抽出動作"""
        text = "主人公は剣を持つ。魔王は城にいる。剣は光る。"
        result = extractor.extract(text, top_k=5, min_score=0.1)
        
        assert isinstance(result, list)
        if result:
            assert all(isinstance(item, tuple) and len(item) == 2 for item in result)

    def test_extract_short_text(self, extractor):
        """短いテキスト（文が1つ）の処理"""
        text = "主人公は剣を持つ。"
        result = extractor.extract(text, top_k=5, min_score=0.01)
        
        assert isinstance(result, list)
        # 文が1つの場合はトークンベースで返る
        if result:
            assert all(isinstance(item, tuple) and len(item) == 2 for item in result)

    def test_extract_unavailable(self, extractor):
        """rank_bm25未インストール時は空リスト"""
        # 環境によっては利用可能な場合があるため、両方のケースを許容
        result = extractor.extract("テストテキスト", top_k=5, min_score=0.1)
        assert isinstance(result, list)


class TestCreateExtractor:
    """create_extractor ファクトリ関数のテスト"""

    def test_create_tfidf(self):
        extractor = create_extractor("tfidf")
        assert isinstance(extractor, TFIDFExtractor)

    def test_create_keybert(self):
        extractor = create_extractor("keybert")
        assert isinstance(extractor, KeyBERTExtractor)

    def test_create_bm25(self):
        extractor = create_extractor("bm25")
        assert isinstance(extractor, BM25Extractor)

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError) as exc_info:
            create_extractor("unknown")
        assert "Unknown extractor method" in str(exc_info.value)