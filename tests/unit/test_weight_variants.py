"""Unit tests for weight variant registry."""

import pytest

from src.config.weight_variants import (
    DEFAULT_WEIGHTS,
    SPECIALIST_NAMES,
    WEIGHT_VARIANTS,
    validate_weights,
    get_variant,
    register_variant,
    list_variants,
    select_variant_for_genre,
    select_variant_for_phase,
    merge_genre_phase_variants,
)


def reset_weight_variants():
    """Reset WEIGHT_VARIANTS to built-in defaults."""
    from src.config.weight_variants import WEIGHT_VARIANTS as WV
    WV.clear()
    WV.update({
        "default_v1": DEFAULT_WEIGHTS.copy(),
        "literary_v1": {
            "consistency": 0.20, "creativity": 0.15, "reader_hook": 0.15,
            "emotion_curve": 0.15, "style": 0.10, "factual": 0.10,
            "structure": 0.10, "multimodal": 0.05,
        },
        "entertainment_v1": {
            "consistency": 0.15, "creativity": 0.15, "reader_hook": 0.25,
            "emotion_curve": 0.15, "style": 0.10, "factual": 0.10,
            "structure": 0.05, "multimodal": 0.05,
        },
        "educational_v1": {
            "consistency": 0.20, "creativity": 0.10, "reader_hook": 0.15,
            "emotion_curve": 0.15, "style": 0.10, "factual": 0.20,
            "structure": 0.10, "multimodal": 0.00,
        },
        "romance_v1": {
            "consistency": 0.15, "creativity": 0.15, "reader_hook": 0.10,
            "emotion_curve": 0.25, "style": 0.10, "factual": 0.10,
            "structure": 0.10, "multimodal": 0.05,
        },
        "mystery_v1": {
            "consistency": 0.25, "creativity": 0.10, "reader_hook": 0.10,
            "emotion_curve": 0.10, "style": 0.05, "factual": 0.05,
            "structure": 0.25, "multimodal": 0.10,
        },
        "planning_v1": {
            "consistency": 0.15, "creativity": 0.25, "reader_hook": 0.05,
            "emotion_curve": 0.15, "style": 0.05, "factual": 0.10,
            "structure": 0.15, "multimodal": 0.10,
        },
        "mid_writing_v1": {
            "consistency": 0.25, "creativity": 0.05, "reader_hook": 0.10,
            "emotion_curve": 0.20, "style": 0.05, "factual": 0.20,
            "structure": 0.10, "multimodal": 0.05,
        },
        "climax_v1": {
            "consistency": 0.15, "creativity": 0.10, "reader_hook": 0.20,
            "emotion_curve": 0.25, "style": 0.05, "factual": 0.15,
            "structure": 0.05, "multimodal": 0.05,
        },
        "literary_v2_consistency_up": {
            "consistency": 0.25, "creativity": 0.15, "reader_hook": 0.10,
            "emotion_curve": 0.15, "style": 0.10, "factual": 0.10,
            "structure": 0.10, "multimodal": 0.05,
        },
        "entertainment_v2_hook_up": {
            "consistency": 0.10, "creativity": 0.15, "reader_hook": 0.30,
            "emotion_curve": 0.15, "style": 0.10, "factual": 0.10,
            "structure": 0.05, "multimodal": 0.05,
        },
        "mystery_v2_structure_up": {
            "consistency": 0.20, "creativity": 0.10, "reader_hook": 0.10,
            "emotion_curve": 0.10, "style": 0.05, "factual": 0.05,
            "structure": 0.30, "multimodal": 0.10,
        },
        "balanced_v1": {
            "consistency": 0.125, "creativity": 0.125, "reader_hook": 0.125,
            "emotion_curve": 0.125, "style": 0.125, "factual": 0.125,
            "structure": 0.125, "multimodal": 0.125,
        },
    })


class TestValidateWeights:
    def setup_method(self):
        reset_weight_variants()

    def test_valid_default_weights(self):
        """Default weights should be valid."""
        validate_weights(DEFAULT_WEIGHTS)

    def test_missing_specialist_raises(self):
        """Missing specialist should raise ValueError."""
        weights = DEFAULT_WEIGHTS.copy()
        del weights["consistency"]
        with pytest.raises(ValueError, match="Missing weights"):
            validate_weights(weights)

    def test_extra_specialist_raises(self):
        """Extra unknown specialist should raise ValueError."""
        weights = DEFAULT_WEIGHTS.copy()
        weights["unknown"] = 0.1
        with pytest.raises(ValueError, match="Unknown specialist"):
            validate_weights(weights)

    def test_sum_not_one_raises(self):
        """Weights not summing to 1.0 should raise ValueError."""
        weights = {k: 0.1 for k in SPECIALIST_NAMES}  # Sum = 0.8
        with pytest.raises(ValueError, match="sum to 1.0"):
            validate_weights(weights)

    def test_valid_custom_weights(self):
        """Custom valid weights should pass."""
        weights = {
            "consistency": 0.25, "creativity": 0.15, "reader_hook": 0.20,
            "emotion_curve": 0.15, "style": 0.05, "factual": 0.10,
            "structure": 0.05, "multimodal": 0.05,
        }
        validate_weights(weights)


class TestGetVariant:
    def setup_method(self):
        reset_weight_variants()

    def test_get_existing_variant(self):
        """Getting existing variant returns copy."""
        variant = get_variant("default_v1")
        assert variant == DEFAULT_WEIGHTS
        # Should be a copy, not the same object
        variant["consistency"] = 0.99
        assert get_variant("default_v1")["consistency"] == 0.20

    def test_get_genre_variant(self):
        """Genre variants accessible."""
        literary = get_variant("literary_v1")
        assert literary["emotion_curve"] == 0.15
        assert literary["multimodal"] == 0.05

    def test_get_phase_variant(self):
        """Phase variants accessible."""
        planning = get_variant("planning_v1")
        assert planning["creativity"] == 0.25
        assert planning["reader_hook"] == 0.05

    def test_get_experimental_variant(self):
        """Experimental variants accessible."""
        exp = get_variant("literary_v2_consistency_up")
        assert exp["consistency"] == 0.25
        assert exp["creativity"] == 0.15

    def test_get_unknown_raises(self):
        """Unknown variant raises KeyError."""
        with pytest.raises(KeyError):
            get_variant("nonexistent_variant")


class TestRegisterVariant:
    def setup_method(self):
        reset_weight_variants()

    def test_register_new_variant(self):
        """Can register new variant."""
        new_weights = {
            "consistency": 0.30, "creativity": 0.10, "reader_hook": 0.10,
            "emotion_curve": 0.10, "style": 0.10, "factual": 0.10,
            "structure": 0.10, "multimodal": 0.10,
        }
        register_variant("test_custom", new_weights)
        assert "test_custom" in WEIGHT_VARIANTS
        assert get_variant("test_custom") == new_weights

    def test_register_invalid_weights_raises(self):
        """Registering invalid weights raises ValueError."""
        with pytest.raises(ValueError):
            register_variant("bad", {"consistency": 0.5})  # Missing others

    def test_register_overwrite_false_raises(self):
        """Cannot overwrite without overwrite=True."""
        with pytest.raises(KeyError):
            register_variant("default_v1", DEFAULT_WEIGHTS)

    def test_register_overwrite_true(self):
        """Can overwrite with overwrite=True."""
        new_weights = {
            "consistency": 0.30, "creativity": 0.10, "reader_hook": 0.10,
            "emotion_curve": 0.10, "style": 0.10, "factual": 0.10,
            "structure": 0.10, "multimodal": 0.10,
        }
        register_variant("default_v1", new_weights, overwrite=True)
        assert get_variant("default_v1") == new_weights

    def test_register_extra_keys_raises(self):
        """Extra keys in weights raises ValueError."""
        weights = DEFAULT_WEIGHTS.copy()
        weights["extra"] = 0.1
        with pytest.raises(ValueError, match="Unknown specialist"):
            register_variant("test_extra", weights)


class TestListVariants:
    def setup_method(self):
        reset_weight_variants()

    def test_list_contains_expected(self):
        """List contains all expected variants."""
        variants = list_variants()
        assert "default_v1" in variants
        assert "literary_v1" in variants
        assert "entertainment_v1" in variants
        assert "planning_v1" in variants
        assert "literary_v2_consistency_up" in variants
        assert len(variants) >= 13  # At least the built-in ones


class TestSelectVariant:
    def setup_method(self):
        reset_weight_variants()

    def test_select_genre_default(self):
        """Unknown genre falls back to default."""
        assert select_variant_for_genre("unknown") == "default_v1"

    def test_select_known_genre(self):
        """Known genre returns genre variant."""
        assert select_variant_for_genre("literary") == "literary_v1"
        assert select_variant_for_genre("mystery") == "mystery_v1"

    def test_select_phase_default(self):
        """Unknown phase falls back to default."""
        assert select_variant_for_phase("unknown") == "default_v1"

    def test_select_known_phase(self):
        """Known phase returns phase variant."""
        assert select_variant_for_phase("planning") == "planning_v1"
        assert select_variant_for_phase("climax") == "climax_v1"


class TestMergeGenrePhase:
    def setup_method(self):
        reset_weight_variants()

    def test_merge_basic(self):
        """Merge combines genre and phase variants."""
        merged = merge_genre_phase_variants("literary", "planning")
        # Phase should override genre for overlapping keys
        # literary has creativity=0.15, planning has creativity=0.25
        assert merged["creativity"] == 0.25  # Phase wins
        # Both have consistency, phase wins
        assert merged["consistency"] == 0.15  # Phase wins

    def test_merge_renormalizes(self):
        """Merge renormalizes to sum=1.0."""
        merged = merge_genre_phase_variants("literary", "planning")
        total = sum(merged.values())
        assert abs(total - 1.0) < 1e-6

    def test_merge_unknown_genre_phase(self):
        """Unknown genre/phase uses defaults (both fall back to default_v1)."""
        merged = merge_genre_phase_variants("unknown_genre", "unknown_phase")
        # Both fall back to default_v1, merge = default_v1 + default_v1 = default_v1
        assert merged == DEFAULT_WEIGHTS


class TestBuiltinVariantsValid:
    def setup_method(self):
        reset_weight_variants()

    def test_all_builtins_valid(self):
        """All built-in variants pass validation."""
        for name, weights in WEIGHT_VARIANTS.items():
            validate_weights(weights)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])