"""LLM Bias Correction Utility.

Phase 2 / Guideline #3: Post-hoc multiplicative correction for LLM judge bias.
Each specialist may have systematic bias (lenient/harsh); this module applies
pre-computed correction factors to normalize scores.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Default correction factors (neutral = 1.0)
DEFAULT_CORRECTIONS = {
    "consistency": 1.0,
    "creativity": 1.0,
    "reader_hook": 1.0,
    "emotion_curve": 1.0,
    "style": 1.0,
    "factual": 1.0,
    "structure": 1.0,
    "multimodal": 1.0,
}

_correction_cache: dict[str, float] | None = None


def load_bias_corrections(config_path: str = "config/llm_bias_correction.yaml") -> dict[str, float]:
    """Load bias correction factors from YAML config.

    Args:
        config_path: Path to YAML config file

    Returns:
        Dict mapping specialist_name -> correction_factor
    """
    global _correction_cache
    if _correction_cache is not None:
        return _correction_cache

    try:
        path = Path(config_path)
        if not path.is_absolute():
            # Try relative to project root
            import os
            project_root = os.getenv("PROJECT_ROOT", ".")
            path = Path(project_root) / config_path

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        corrections = data.get("bias_correction", DEFAULT_CORRECTIONS)
        # Validate all specialists present
        for spec in DEFAULT_CORRECTIONS:
            if spec not in corrections:
                corrections[spec] = 1.0
                logger.warning(f"Missing correction factor for {spec}, using 1.0")

        _correction_cache = corrections
        logger.info(f"Loaded LLM bias corrections: {corrections}")
        return corrections

    except Exception as e:
        logger.warning(f"Failed to load bias corrections from {config_path}: {e}, using defaults")
        _correction_cache = DEFAULT_CORRECTIONS.copy()
        return _correction_cache


def apply_bias_correction(score: float, specialist_name: str, config_path: str = "config/llm_bias_correction.yaml") -> float:
    """Apply bias correction to a specialist score.

    Args:
        score: Raw score from LLM (0-100)
        specialist_name: Name of the specialist
        config_path: Path to YAML config file

    Returns:
        Corrected score, clipped to [0, 100]
    """
    corrections = load_bias_corrections(config_path)
    factor = corrections.get(specialist_name, 1.0)
    corrected = score * factor
    return max(0.0, min(100.0, round(corrected, 1)))


def compute_correction_factors_from_logs(
    log_entries: list[dict[str, Any]],
    target_median: float = 75.0,
) -> dict[str, float]:
    """Compute correction factors from historical audit logs.

    Args:
        log_entries: List of dicts with keys: specialist_name, score, confidence
        target_median: Desired median score after correction

    Returns:
        Dict mapping specialist_name -> correction_factor
    """
    from collections import defaultdict
    import statistics

    scores_by_spec = defaultdict(list)
    for entry in log_entries:
        spec = entry.get("specialist_name")
        score = entry.get("score")
        conf = entry.get("confidence", 1.0)
        if spec and score is not None and conf >= 0.6:  # Only high-confidence entries
            scores_by_spec[spec].append(score)

    factors = {}
    for spec, scores in scores_by_spec.items():
        if len(scores) >= 5:  # Minimum samples for reliable median
            observed_median = statistics.median(scores)
            if observed_median > 0:
                factors[spec] = round(target_median / observed_median, 3)
            else:
                factors[spec] = 1.0
        else:
            factors[spec] = 1.0

    # Fill missing with 1.0
    for spec in DEFAULT_CORRECTIONS:
        if spec not in factors:
            factors[spec] = 1.0

    return factors


def save_correction_factors(
    factors: dict[str, float],
    config_path: str = "config/llm_bias_correction.yaml",
) -> None:
    """Save correction factors to YAML config.

    Args:
        factors: Dict mapping specialist_name -> correction_factor
        config_path: Path to YAML config file
    """
    data = {"bias_correction": factors}
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=True)


__all__ = [
    "load_bias_corrections",
    "apply_bias_correction",
    "compute_correction_factors_from_logs",
    "save_correction_factors",
    "DEFAULT_CORRECTIONS",
]