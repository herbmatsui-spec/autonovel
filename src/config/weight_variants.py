"""Weight Variant Registry for A/B Testing.

Phase 2 / Guideline #3: Manages weight variants for genre/phase-specific
audit weighting with validation and dynamic registration.
"""

from __future__ import annotations

import logging

import yaml

logger = logging.getLogger(__name__)

# Default weights (must sum to 1.0)
DEFAULT_WEIGHTS = {
    "consistency": 0.20,
    "creativity": 0.15,
    "reader_hook": 0.15,
    "emotion_curve": 0.10,
    "style": 0.10,
    "factual": 0.10,
    "structure": 0.10,
    "multimodal": 0.10,
}

SPECIALIST_NAMES = tuple(DEFAULT_WEIGHTS.keys())
WEIGHT_TOLERANCE = 1e-6

# Built-in variants (can be extended via register_variant)
WEIGHT_VARIANTS: dict[str, dict[str, float]] = {
    # Base variants
    "default_v1": DEFAULT_WEIGHTS.copy(),

    # Genre-specific variants (v1 = current production)
    "literary_v1": {
        "consistency": 0.20,
        "creativity": 0.15,
        "reader_hook": 0.15,
        "emotion_curve": 0.15,
        "style": 0.10,
        "factual": 0.10,
        "structure": 0.10,
        "multimodal": 0.05,
    },
    "entertainment_v1": {
        "consistency": 0.15,
        "creativity": 0.15,
        "reader_hook": 0.25,
        "emotion_curve": 0.15,
        "style": 0.10,
        "factual": 0.10,
        "structure": 0.05,
        "multimodal": 0.05,
    },
    "educational_v1": {
        "consistency": 0.20,
        "creativity": 0.10,
        "reader_hook": 0.15,
        "emotion_curve": 0.15,
        "style": 0.10,
        "factual": 0.20,
        "structure": 0.10,
        "multimodal": 0.00,
    },
    "romance_v1": {
        "consistency": 0.15,
        "creativity": 0.15,
        "reader_hook": 0.10,
        "emotion_curve": 0.25,
        "style": 0.10,
        "factual": 0.10,
        "structure": 0.10,
        "multimodal": 0.05,
    },
    "mystery_v1": {
        "consistency": 0.25,
        "creativity": 0.10,
        "reader_hook": 0.10,
        "emotion_curve": 0.10,
        "style": 0.05,
        "factual": 0.05,
        "structure": 0.25,
        "multimodal": 0.10,
    },

    # Phase-specific variants
    "planning_v1": {
        "consistency": 0.15,
        "creativity": 0.25,
        "reader_hook": 0.05,
        "emotion_curve": 0.15,
        "style": 0.05,
        "factual": 0.10,
        "structure": 0.15,
        "multimodal": 0.10,
    },
    "mid_writing_v1": {
        "consistency": 0.25,
        "creativity": 0.05,
        "reader_hook": 0.10,
        "emotion_curve": 0.20,
        "style": 0.05,
        "factual": 0.20,
        "structure": 0.10,
        "multimodal": 0.05,
    },
    "climax_v1": {
        "consistency": 0.15,
        "creativity": 0.10,
        "reader_hook": 0.20,
        "emotion_curve": 0.25,
        "style": 0.05,
        "factual": 0.15,
        "structure": 0.05,
        "multimodal": 0.05,
    },

    # Experimental variants (for A/B testing)
    "literary_v2_consistency_up": {
        "consistency": 0.25,
        "creativity": 0.15,
        "reader_hook": 0.10,
        "emotion_curve": 0.15,
        "style": 0.10,
        "factual": 0.10,
        "structure": 0.10,
        "multimodal": 0.05,
    },
    "entertainment_v2_hook_up": {
        "consistency": 0.10,
        "creativity": 0.15,
        "reader_hook": 0.30,
        "emotion_curve": 0.15,
        "style": 0.10,
        "factual": 0.10,
        "structure": 0.05,
        "multimodal": 0.05,
    },
    "mystery_v2_structure_up": {
        "consistency": 0.20,
        "creativity": 0.10,
        "reader_hook": 0.10,
        "emotion_curve": 0.10,
        "style": 0.05,
        "factual": 0.05,
        "structure": 0.30,
        "multimodal": 0.10,
    },
    "balanced_v1": {
        "consistency": 0.125,
        "creativity": 0.125,
        "reader_hook": 0.125,
        "emotion_curve": 0.125,
        "style": 0.125,
        "factual": 0.125,
        "structure": 0.125,
        "multimodal": 0.125,
    },
}


def validate_weights(weights: dict[str, float]) -> None:
    """Validate weight dict has all specialists and sums to 1.0."""
    missing = [n for n in SPECIALIST_NAMES if n not in weights]
    if missing:
        raise ValueError(f"Missing weights for specialists: {missing}")

    extra = [n for n in weights if n not in SPECIALIST_NAMES]
    if extra:
        raise ValueError(f"Unknown specialist names in weights: {extra}")

    total = sum(weights[n] for n in SPECIALIST_NAMES)
    if abs(total - 1.0) > WEIGHT_TOLERANCE:
        raise ValueError(
            f"Weights must sum to 1.0 (got {total:.6f}); "
            f"adjust values to sum to 1.0"
        )


def get_variant(name: str) -> dict[str, float]:
    """Get weight variant by name.

    Args:
        name: Variant name (e.g., "literary_v1", "default_v1")

    Returns:
        Weight dict for the variant

    Raises:
        KeyError: If variant not found
    """
    if name not in WEIGHT_VARIANTS:
        raise KeyError(f"Unknown weight variant: {name}. Available: {list(WEIGHT_VARIANTS.keys())}")
    return WEIGHT_VARIANTS[name].copy()


def register_variant(name: str, weights: dict[str, float], overwrite: bool = False) -> None:
    """Register a new weight variant.

    Args:
        name: Variant name (e.g., "genre_v2_experiment")
        weights: Weight dict (must be valid)
        overwrite: If True, allow overwriting existing variant

    Raises:
        ValueError: If weights invalid
        KeyError: If variant exists and overwrite=False
    """
    validate_weights(weights)

    if name in WEIGHT_VARIANTS and not overwrite:
        raise KeyError(f"Variant '{name}' already exists. Use overwrite=True to replace.")

    WEIGHT_VARIANTS[name] = weights.copy()
    logger.info(f"Registered weight variant: {name} -> {weights}")


def list_variants() -> list[str]:
    """List all registered variant names."""
    return sorted(WEIGHT_VARIANTS.keys())


def load_variants_from_yaml(config_path: str) -> dict[str, dict[str, float]]:
    """Load weight variants from YAML file and register them.

    Args:
        config_path: Path to YAML file with variants

    Returns:
        Dict of loaded variants
    """
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    loaded = {}

    # Load default
    if "default" in data:
        register_variant("default_v1", data["default"], overwrite=True)
        loaded["default_v1"] = data["default"]

    # Load genre variants
    for genre, weights in data.get("by_genre", {}).items():
        name = f"{genre}_v1"
        register_variant(name, weights, overwrite=True)
        loaded[name] = weights

    # Load phase variants
    for phase, weights in data.get("by_phase", {}).items():
        name = f"{phase}_v1"
        register_variant(name, weights, overwrite=True)
        loaded[name] = weights

    logger.info(f"Loaded {len(loaded)} weight variants from {config_path}")
    return loaded


def select_variant_for_genre(genre: str) -> str:
    """Select appropriate variant for a genre.

    Args:
        genre: Genre name

    Returns:
        Variant name (falls back to default_v1 if genre not found)
    """
    variant_name = f"{genre}_v1"
    if variant_name in WEIGHT_VARIANTS:
        return variant_name
    return "default_v1"


def select_variant_for_phase(phase: str) -> str:
    """Select appropriate variant for a writing phase.

    Args:
        phase: Phase name

    Returns:
        Variant name (falls back to default_v1 if phase not found)
    """
    variant_name = f"{phase}_v1"
    if variant_name in WEIGHT_VARIANTS:
        return variant_name
    return "default_v1"


def merge_genre_phase_variants(genre: str, phase: str) -> dict[str, float]:
    """Merge genre and phase variants (phase takes precedence for overlapping keys).

    This is a simple merge; for production use, consider more sophisticated
    combination strategies (e.g., weighted average).
    """
    genre_variant = get_variant(select_variant_for_genre(genre))
    phase_variant = get_variant(select_variant_for_phase(phase))

    # Phase variant overrides genre variant
    merged = genre_variant.copy()
    merged.update(phase_variant)

    # Renormalize to ensure sum = 1.0
    total = sum(merged.values())
    if total > 0:
        merged = {k: v / total for k, v in merged.items()}

    return merged


__all__ = [
    "DEFAULT_WEIGHTS",
    "SPECIALIST_NAMES",
    "WEIGHT_VARIANTS",
    "validate_weights",
    "get_variant",
    "register_variant",
    "list_variants",
    "load_variants_from_yaml",
    "select_variant_for_genre",
    "select_variant_for_phase",
    "merge_genre_phase_variants",
]