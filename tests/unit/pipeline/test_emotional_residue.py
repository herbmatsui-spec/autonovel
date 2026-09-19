"""Tests for emotional residue data structures."""
from __future__ import annotations

import pytest

from src.pipeline.emotional_residue import EmotionType, EmotionalSignal, EmotionalVector


class TestEmotionalVectorCreation:
    """EmotionalVector の基本作成テスト"""

    def test_basic_creation(self):
        vec = EmotionalVector(episode_id="ep01")
        assert vec.episode_id == "ep01"
        assert vec.signals == {}
        assert vec.confidences == {}

    def test_set_and_get_signal(self):
        vec = EmotionalVector(episode_id="ep01")
        signal = EmotionalSignal(
            source="A",
            target="B",
            emotion_type=EmotionType.AFFECTION,
            value=0.5,
            confidence=0.8,
            evidence_span="AはBを信頼していた",
            episode_id="ep01",
            cause="ep01_rescue"
        )
        vec.set_signal(signal)
        
        assert vec.get_value("A", "B", EmotionType.AFFECTION) == 0.5
        assert vec.get_confidence("A", "B", EmotionType.AFFECTION) == 0.8
        assert vec.get_cause("A", "B", EmotionType.AFFECTION) == "ep01_rescue"

    def test_signal_merge_weighted_average(self):
        """同一シグナルの重み付き平均マージテスト"""
        vec = EmotionalVector(episode_id="ep01")
        
        # 最初のシグナル
        sig1 = EmotionalSignal(
            source="A", target="B", emotion_type=EmotionType.AFFECTION,
            value=0.8, confidence=0.6, evidence_span="...", episode_id="ep01"
        )
        vec.set_signal(sig1)
        assert vec.get_value("A", "B", EmotionType.AFFECTION) == 0.8
        
        # 2つ目のシグナル（異なる値・信頼度）
        sig2 = EmotionalSignal(
            source="A", target="B", emotion_type=EmotionType.AFFECTION,
            value=0.2, confidence=0.9, evidence_span="...", episode_id="ep01"
        )
        vec.set_signal(sig2)
        
        # 重み付き平均: (0.8*0.6 + 0.2*0.9) / (0.6+0.9) = 0.66 / 1.5 = 0.44
        expected = (0.8 * 0.6 + 0.2 * 0.9) / 1.5
        assert abs(vec.get_value("A", "B", EmotionType.AFFECTION) - expected) < 0.01
        assert vec.get_confidence("A", "B", EmotionType.AFFECTION) == 1.0  # min(1.0, 1.5)

    def test_get_pair_emotions(self):
        vec = EmotionalVector(episode_id="ep01")
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.5, 0.8, "...", "ep01"))
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.TENSION, 0.7, 0.6, "...", "ep01"))
        vec.set_signal(EmotionalSignal("B", "A", EmotionType.FEAR, 0.3, 0.7, "...", "ep01"))
        
        pair_emos = vec.get_pair_emotions("A", "B")
        assert EmotionType.AFFECTION in pair_emos
        assert EmotionType.TENSION in pair_emos
        assert EmotionType.FEAR not in pair_emos
        assert pair_emos[EmotionType.AFFECTION] == 0.5

    def test_get_top_pairs(self):
        vec = EmotionalVector(episode_id="ep01")
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.5, 0.8, "...", "ep01"))
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.TENSION, 0.7, 0.6, "...", "ep01"))
        vec.set_signal(EmotionalSignal("C", "D", EmotionType.FEAR, 0.2, 0.7, "...", "ep01"))
        
        top = vec.get_top_pairs(limit=2)
        assert len(top) == 2
        # A->B の方が総強度が高い (0.5+0.7=1.2 > 0.2)
        assert top[0][0] == ("A", "B")

    def test_serialization_roundtrip(self):
        vec = EmotionalVector(episode_id="ep01")
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.5, 0.8, "...", "ep01", "cause1"))
        vec.metadata["source"] = "test"
        
        data = vec.to_dict()
        restored = EmotionalVector.from_dict(data)
        
        assert restored.episode_id == "ep01"
        assert restored.get_value("A", "B", EmotionType.AFFECTION) == 0.5
        assert restored.get_confidence("A", "B", EmotionType.AFFECTION) == 0.8
        assert restored.get_cause("A", "B", EmotionType.AFFECTION) == "cause1"
        assert restored.metadata["source"] == "test"

    def test_value_clamping(self):
        """値が -1.0 ~ 1.0 にクランプされること"""
        sig = EmotionalSignal("A", "B", EmotionType.AFFECTION, 1.5, 0.8, "...", "ep01")
        assert sig.value == 1.0
        
        sig2 = EmotionalSignal("A", "B", EmotionType.AFFECTION, -1.5, 0.8, "...", "ep01")
        assert sig2.value == -1.0

    def test_confidence_clamping(self):
        """信頼度が 0.0 ~ 1.0 にクランプされること"""
        sig = EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.5, 1.5, "...", "ep01")
        assert sig.confidence == 1.0
        
        sig2 = EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.5, -0.5, "...", "ep01")
        assert sig2.confidence == 0.0


class TestEmotionType:
    """EmotionType 列挙のテスト"""

    def test_all_emotions_exist(self):
        expected = {
            "affection", "tension", "fear", "trust", "intimacy",
            "jealousy", "anger", "sadness", "surprise", "disgust"
        }
        actual = {e.value for e in EmotionType}
        assert actual == expected

    def test_string_conversion(self):
        assert EmotionType("affection") == EmotionType.AFFECTION
        # str(Enum) returns 'EnumClass.VALUE', use value attribute for string value
        assert EmotionType.AFFECTION.value == "affection"
        assert EmotionType.AFFECTION == "affection"  # str-Enum comparison works