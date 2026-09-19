"""Tests for beat validator."""
from __future__ import annotations

import pytest

from src.annotations.validator import BeatValidator, ValidationResult, validate_beats
from src.annotations.beat import EmotionalBeat
from src.pipeline.emotional_residue import EmotionType


class TestBeatValidator:
    """ビート検証テスト"""

    @pytest.fixture
    def char_dict(self):
        return {"A", "B", "C", "D"}

    @pytest.fixture
    def validator(self, char_dict):
        return BeatValidator(char_dict)

    def test_valid_beats_pass(self, validator):
        """正常なビートは通過"""
        beats = [
            EmotionalBeat(1, 1, "A", "B", EmotionType.FEAR, 0.5, "test"),
            EmotionalBeat(1, 1, "B", "A", EmotionType.AFFECTION, 0.3, "test2"),
        ]
        result = validator.validate(beats)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_unknown_character_error(self, validator):
        """未知のキャラでエラー"""
        beats = [
            EmotionalBeat(1, 1, "X", "B", EmotionType.FEAR, 0.5, "test"),
        ]
        result = validator.validate(beats)
        assert not result.is_valid
        assert any("Unknown source character" in e for e in result.errors)

    def test_delta_out_of_range_error(self, validator):
        """delta範囲外でエラー - EmotionalBeatでクランプされるためスキップ"""
        pytest.skip("EmotionalBeat clamps values in __post_init__")

    def test_confidence_out_of_range_error(self, validator):
        """confidence範囲外でエラー - EmotionalBeatでクランプされるためスキップ"""
        pytest.skip("EmotionalBeat clamps values in __post_init__")

    def test_empty_cause_warning(self, validator):
        """空のcauseで警告"""
        beats = [
            EmotionalBeat(1, 1, "A", "B", EmotionType.FEAR, 0.5, ""),
        ]
        result = validator.validate(beats)
        assert result.is_valid  # 警告のみ
        assert any("Empty cause" in w for w in result.warnings)

    def test_hidden_contradiction_warning(self, validator):
        """hiddenと表向きの矛盾で警告（異なる感情）"""
        beats = [
            EmotionalBeat(1, 1, "A", "B", EmotionType.FEAR, 0.8, "hidden", hidden=True),
            EmotionalBeat(1, 1, "A", "B", EmotionType.TRUST, 0.6, "overt", hidden=False),
        ]
        result = validator.validate(beats)
        assert result.is_valid
        # FEAR と TRUST は contradiction_pairs に含まれるため警告が出る
        assert any("contradiction" in w.lower() for w in result.warnings)

    def test_same_emotion_sign_contradiction_warning(self, validator):
        """同じ感情で符号逆で警告"""
        beats = [
            EmotionalBeat(1, 1, "A", "B", EmotionType.FEAR, 0.8, "hidden", hidden=True),
            EmotionalBeat(1, 1, "A", "B", EmotionType.FEAR, -0.5, "overt", hidden=False),
        ]
        result = validator.validate(beats)
        assert result.is_valid
        assert any("sign contradiction" in w.lower() for w in result.warnings)

    def test_duplicate_same_delta_ok(self, validator):
        """同一deltaなら重複OK"""
        beats = [
            EmotionalBeat(1, 1, "A", "B", EmotionType.FEAR, 0.5, "test1"),
            EmotionalBeat(1, 1, "A", "B", EmotionType.FEAR, 0.5, "test2"),
        ]
        result = validator.validate(beats)
        assert result.is_valid

    def test_duplicate_different_delta_warning(self, validator):
        """同一キー異なるdeltaで警告"""
        beats = [
            EmotionalBeat(1, 1, "A", "B", EmotionType.FEAR, 0.5, "test1"),
            EmotionalBeat(1, 1, "A", "B", EmotionType.FEAR, 0.8, "test2"),
        ]
        result = validator.validate(beats)
        assert result.is_valid
        assert any("different delta" in w for w in result.warnings)

    def test_convenience_function(self):
        """便利関数 validate_beats"""
        beats = [EmotionalBeat(1, 1, "A", "B", EmotionType.FEAR, 0.5, "test")]
        result = validate_beats(beats, {"A", "B"})
        assert result.is_valid


class TestValidationResult:
    """ValidationResult データクラステスト"""

    def test_result_creation(self):
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["warning1"],
        )
        assert result.is_valid
        assert result.warnings == ["warning1"]

    def test_result_invalid(self):
        result = ValidationResult(
            is_valid=False,
            errors=["error1"],
            warnings=[],
        )
        assert not result.is_valid
        assert result.errors == ["error1"]