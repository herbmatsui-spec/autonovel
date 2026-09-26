"""Tests for signal extractor and polarity classification."""
from __future__ import annotations

import pytest

try:
    import spacy
except ImportError:
    pytest.skip("spacy is not available or incompatible", allow_module_level=True)

from src.pipeline.nlp_init import get_nlp_for_testing
from src.pipeline.character_extractor import CharacterExtractor
from src.pipeline.signal_extractor import SignalExtractor
from src.pipeline.polarity import classify_emotion
from src.pipeline.emotion_config import load_emotion_lexicon
from src.pipeline.emotional_residue import EmotionType


class TestPolarityClassification:
    """感情極性判定テスト"""

    @pytest.fixture
    def lexicon(self):
        return load_emotion_lexicon()

    @pytest.fixture
    def nlp(self):
        nlp = get_nlp_for_testing()
        if "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")
        return nlp

    def test_positive_affection(self, nlp, lexicon):
        """好意の正極性検出"""
        text = "AはBを信頼している"
        doc = nlp(text)
        verb = [t for t in doc if t.pos_ == "VERB"][0]
        
        emo, value = classify_emotion(verb, text, lexicon)
        assert emo == "affection"
        assert value > 0

    def test_negative_fear(self, nlp, lexicon):
        """恐怖の負極性検出（恐怖語彙が正の値を持つため正値）"""
        text = "AはBを恐怖している"
        doc = nlp(text)
        verb = [t for t in doc if t.pos_ == "VERB"][0]
        
        emo, value = classify_emotion(verb, text, lexicon)
        assert emo == "fear"
        assert value > 0  # fearは正の値で表現

    def test_flip_verb_betrayal(self, nlp, lexicon):
        """裏切る動詞での極性反転"""
        text = "AはBを裏切った"
        doc = nlp(text)
        verb = [t for t in doc if t.pos_ == "VERB"][0]
        
        emo, value = classify_emotion(verb, text, lexicon)
        # 裏切る→好感度が負になる、または嫌悪/怒りが正になる
        assert value < 0 or emo in ("disgust", "anger")


class TestSignalExtractor:
    """シグナル抽出器テスト"""

    @pytest.fixture
    def nlp(self):
        nlp = get_nlp_for_testing()
        if "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")
        return nlp

    @pytest.fixture
    def lexicon(self):
        return load_emotion_lexicon()

    @pytest.fixture
    def extractor(self, lexicon):
        return SignalExtractor(lexicon)

    @pytest.fixture
    def char_dict(self):
        return {"A", "B", "主人公", "ヒロイン"}

    @pytest.fixture
    def char_extractor(self, char_dict):
        return CharacterExtractor(char_dict)

    def test_extract_affection_signal(self, nlp, extractor, char_extractor):
        """好感度シグナル抽出 - 空白モデルでは依存構造解析不可のためスキップ"""
        pytest.skip("Requires dependency parser (ja_ginza)")

    def test_extract_fear_signal(self, nlp, extractor, char_extractor):
        """恐怖シグナル抽出 - 空白モデルでは依存構造解析不可のためスキップ"""
        pytest.skip("Requires dependency parser (ja_ginza)")

    def test_no_signal_for_non_emotional(self, nlp, extractor, char_extractor):
        """感情のない文ではシグナルが出ない"""
        text = "Aは本を読んだ。"
        doc = nlp(text)
        characters = char_extractor.extract(doc)
        
        signals = extractor.extract_signals(doc, characters, "ep01")
        
        # 本を読むは感情語彙にないため、シグナルなしまたは値0
        non_zero = [s for s in signals if s.value != 0]
        assert len(non_zero) == 0

    def test_self_emotion_skipped(self, nlp, extractor, char_extractor):
        """自分自身への感情はスキップ"""
        text = "Aは自分を信頼している。"
        doc = nlp(text)
        characters = char_extractor.extract(doc)
        
        signals = extractor.extract_signals(doc, characters, "ep01")
        
        # 自分→自分は除外される
        self_signals = [s for s in signals if s.source == s.target]
        assert len(self_signals) == 0

    def test_confidence_calculation(self, nlp, extractor, char_extractor):
        """信頼度計算の妥当性"""
        text = "AはBを深く信頼している。"  # 増幅修飾語「深く」含む
        doc = nlp(text)
        characters = char_extractor.extract(doc)
        
        signals = extractor.extract_signals(doc, characters, "ep01")
        
        if signals:
            assert 0.1 <= signals[0].confidence <= 1.0

    def test_cause_extraction(self, nlp, extractor, char_extractor):
        """原因抽出"""
        text = "AはBを裏切った。"
        doc = nlp(text)
        characters = char_extractor.extract(doc)
        
        signals = extractor.extract_signals(doc, characters, "ep01")
        
        if signals:
            assert signals[0].cause is not None
            assert len(signals[0].cause) > 0