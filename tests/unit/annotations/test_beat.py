"""Tests for EmotionalBeat data class."""
from __future__ import annotations

import pytest

from src.annotations.beat import EmotionalBeat
from src.pipeline.emotional_residue import EmotionType, EmotionalSignal


class TestEmotionalBeat:
    """EmotionalBeat バリデーション・変換テスト"""

    def test_beat_creation_valid(self):
        """正常なビート作成"""
        beat = EmotionalBeat(
            episode=14,
            scene=3,
            source="A",
            target="B",
            emotion=EmotionType.FEAR,
            delta=0.6,
            cause="ep14 betrayal witnessed",
        )
        assert beat.episode == 14
        assert beat.scene == 3
        assert beat.source == "A"
        assert beat.target == "B"
        assert beat.emotion == EmotionType.FEAR
        assert beat.delta == 0.6
        assert beat.confidence == 1.0
        assert beat.hidden is False
        assert beat.beat_id is not None

    def test_beat_delta_clamping(self):
        """deltaが-1.0~1.0にクランプ"""
        beat = EmotionalBeat(episode=1, scene=1, source="A", target="B",
                             emotion=EmotionType.AFFECTION, delta=1.5, cause="test")
        assert beat.delta == 1.0

        beat2 = EmotionalBeat(episode=1, scene=1, source="A", target="B",
                              emotion=EmotionType.AFFECTION, delta=-1.5, cause="test")
        assert beat2.delta == -1.0

    def test_beat_confidence_clamping(self):
        """confidenceが0.0~1.0にクランプ"""
        beat = EmotionalBeat(episode=1, scene=1, source="A", target="B",
                             emotion=EmotionType.AFFECTION, delta=0.5, cause="test",
                             confidence=1.5)
        assert beat.confidence == 1.0

    def test_beat_validation_empty_source(self):
        """source空でエラー"""
        with pytest.raises(ValueError, match="source"):
            EmotionalBeat(episode=1, scene=1, source="", target="B",
                          emotion=EmotionType.AFFECTION, delta=0.5, cause="test")

    def test_beat_validation_empty_cause(self):
        """空のcauseはEmotionalBeatでは許可される（バリデーターで警告）"""
        beat = EmotionalBeat(episode=1, scene=1, source="A", target="B",
                             emotion=EmotionType.AFFECTION, delta=0.5, cause="")
        # EmotionalBeat自体は空causeを許可（バリデーターでチェック）
        assert beat.cause == ""

    def test_to_signal_conversion(self):
        """EmotionalSignalへの変換"""
        beat = EmotionalBeat(
            episode=14, scene=3, source="A", target="B",
            emotion=EmotionType.FEAR, delta=0.6,
            cause="ep14 betrayal", confidence=0.9, hidden=True,
        )
        signal = beat.to_signal()
        
        assert isinstance(signal, EmotionalSignal)
        assert signal.source == "A"
        assert signal.target == "B"
        assert signal.emotion_type == EmotionType.FEAR
        assert signal.value == 0.6
        assert signal.confidence == 0.9
        assert signal.episode_id == "ep14"
        assert signal.cause == "ep14 betrayal"
        assert signal.hidden is True

    def test_from_dict_roundtrip(self):
        """辞書変換ラウンドトリップ"""
        original = EmotionalBeat(
            episode=14, scene=3, source="A", target="B",
            emotion=EmotionType.FEAR, delta=0.6,
            cause="ep14 betrayal", confidence=0.8, hidden=True,
            metadata={"note": "important"},
        )
        
        data = original.to_dict()
        restored = EmotionalBeat.from_dict(data, episode=14, scene=3)
        
        assert restored.episode == 14
        assert restored.scene == 3
        assert restored.source == "A"
        assert restored.target == "B"
        assert restored.emotion == EmotionType.FEAR
        assert restored.delta == 0.6
        assert restored.cause == "ep14 betrayal"
        assert restored.confidence == 0.8
        assert restored.hidden is True
        assert restored.metadata == {"note": "important"}

    def test_from_dict_defaults(self):
        """辞書からの構築でデフォルト値適用"""
        data = {
            "source": "A", "target": "B", "emotion": "fear",
            "delta": 0.5, "cause": "test",
        }
        beat = EmotionalBeat.from_dict(data, episode=1, scene=1)
        
        assert beat.confidence == 1.0
        assert beat.hidden is False
        assert beat.beat_id is not None


class TestParsedScript:
    """ParsedScriptテスト"""

    def test_parsed_script_creation(self):
        from src.annotations.beat import ParsedScript
        
        beats = [
            EmotionalBeat(1, 1, "A", "B", EmotionType.AFFECTION, 0.5, "test"),
        ]
        parsed = ParsedScript(
            clean_text="clean",
            beats=beats,
            frontmatter_beats=beats,
            inline_beats=[],
        )
        assert parsed.clean_text == "clean"
        assert len(parsed.beats) == 1