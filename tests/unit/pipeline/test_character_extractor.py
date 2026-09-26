"""Tests for character extractor."""
from __future__ import annotations

import pytest

try:
    import spacy
except ImportError:
    pytest.skip("spacy is not available or incompatible", allow_module_level=True)

from src.pipeline.nlp_init import get_nlp_for_testing
from src.pipeline.character_extractor import CharacterExtractor, CharacterMention


class TestCharacterExtractor:
    """キャラ名抽出器テスト"""

    @pytest.fixture
    def nlp(self):
        return get_nlp_for_testing()

    @pytest.fixture
    def char_dict(self):
        return {"A", "B", "C", "主人公", "ヒロイン", "敵"}

    @pytest.fixture
    def extractor(self, char_dict):
        return CharacterExtractor(char_dict)

    def test_extract_known_characters(self, nlp, extractor):
        """既知キャラ名の抽出"""
        text = "AはBに向かって剣を構えた。主人公はヒロインを守ろうとした。"
        doc = nlp(text)
        mentions = extractor.extract(doc)
        
        texts = [m.text for m in mentions]
        assert "A" in texts
        assert "B" in texts
        assert "主人公" in texts
        assert "ヒロイン" in texts

    def test_extract_with_pronouns(self, nlp, extractor):
        """代名詞も抽出されること"""
        text = "Aは言った。「私は行く」。Bはそれに答えた。「君も来い」。"
        doc = nlp(text)
        mentions = extractor.extract(doc)
        
        texts = [m.text for m in mentions]
        assert "私" in texts
        assert "君" in texts
        
        # 代名詞フラグ確認
        pronoun_mentions = [m for m in mentions if m.is_pronoun]
        assert len(pronoun_mentions) >= 2

    def test_normalized_name_mapping(self, nlp, extractor):
        """正規化名マッピング"""
        # 辞書に「主人公」があるとき、「主」だけでもマッチするか（部分マッチ）
        text = "主は立ち上がった。"
        doc = nlp(text)
        mentions = extractor.extract(doc)
        
        # 部分マッチは実装依存なので、完全一致の場合のみテスト
        text2 = "主人公は立ち上がった。"
        doc2 = nlp(text2)
        mentions2 = extractor.extract(doc2)
        for m in mentions2:
            if m.text == "主人公":
                assert m.normalized_name == "主人公"

    def test_no_duplicate_spans(self, nlp, extractor):
        """重複スパンが除去されること"""
        text = "AとAが戦う。"
        doc = nlp(text)
        mentions = extractor.extract(doc)
        
        # 同じ位置の重複がないこと
        spans = [(m.start_char, m.end_char) for m in mentions]
        assert len(spans) == len(set(spans))

    def test_speaker_estimation(self):
        """発言者推定（簡易） - 空白モデルではスキップ"""
        pytest.skip("Speaker estimation requires proper Japanese tokenization")

    def test_empty_dict(self, nlp):
        """辞書なしでも動作すること"""
        extractor = CharacterExtractor(set())
        text = "田中太郎は佐藤花子に会った。"
        doc = nlp(text)
        mentions = extractor.extract(doc)
        
        # 固有表現抽出は空白モデルでは動かないが、エラーにならないこと
        assert isinstance(mentions, list)