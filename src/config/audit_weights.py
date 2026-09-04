"""Audit weights loader.

Reads ``config/audit_weights.yaml`` and resolves a final weight dict
for a given (genre, phase) combination. Validates that all 8 specialists
are present and that weights sum to 1.0.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.services.audit_aggregator import (
    SPECIALIST_NAMES,
    renormalize,
    validate_weights,
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "audit_weights.yaml"


@lru_cache(maxsize=1)
def _load_yaml(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        logger.warning("audit_weights.yaml not found at %s; using defaults", p)
        return {}
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def clear_cache() -> None:
    _load_yaml.cache_clear()


def load_weights(
    genre: str | None = None,
    phase: str | None = None,
    config_path: str | None = None,
) -> dict[str, float]:
    """Resolve weights for ``(genre, phase)``.

    Layer order:
        default -> by_genre[genre] (or default if unknown) -> by_phase[phase]
    Returns a dict with all 8 specialists. Validates the sum = 1.0.
    """
    cfg = _load_yaml(config_path or str(DEFAULT_CONFIG_PATH))
    weights: dict[str, float] = dict(cfg.get("default") or {})
    if not weights:
        # Hard fallback: equal weights (used only if YAML is missing).
        weights = {n: 1.0 / len(SPECIALIST_NAMES) for n in SPECIALIST_NAMES}

    by_genre = cfg.get("by_genre") or {}
    if genre and genre in by_genre:
        for k, v in (by_genre[genre] or {}).items():
            weights[k] = float(v)

    by_phase = cfg.get("by_phase") or {}
    if phase and phase in by_phase:
        for k, v in (by_phase[phase] or {}).items():
            weights[k] = float(v)

    # Fill any missing specialists with equal share so validate_weights
    # does not raise on partial overrides.
    for n in SPECIALIST_NAMES:
        weights.setdefault(n, 0.0)
    validate_weights(weights)
    return weights


def load_weights_renormalized(
    genre: str | None = None,
    phase: str | None = None,
    present: list[str] | None = None,
    config_path: str | None = None,
) -> dict[str, float]:
    """Like ``load_weights`` but renormalized for the given present
    specialists. If ``present`` is None, returns the full validated map.
    """
    full = load_weights(genre=genre, phase=phase, config_path=config_path)
    if present is None:
        return full
    return renormalize(full, present)


__all__ = ["load_weights", "load_weights_renormalized", "clear_cache"]