"""Anti-AI detection & correction configuration loader.

Reads ``config/anti_ai_config.yaml`` and exposes typed Pydantic
models plus a cached loader. Follows the same pattern as
``src/config/audit_weights.py`` so it slots in cleanly alongside
the existing config layer.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "anti_ai_config.yaml"


# ---------------------------------------------------------------------------
# Detector settings
# ---------------------------------------------------------------------------
class TransitionOveruseSettings(BaseModel):
    enabled: bool = True
    density_threshold: float = Field(default=0.33, ge=0.0, le=1.0)
    weight: float = Field(default=1.0, ge=0.0)


class SameStructureSettings(BaseModel):
    enabled: bool = True
    consecutive_count: int = Field(default=3, ge=2)
    weight: float = Field(default=1.5, ge=0.0)


class DirectEmotionSettings(BaseModel):
    enabled: bool = True
    per_paragraph_limit: int = Field(default=2, ge=1)
    weight: float = Field(default=1.0, ge=0.0)


class HedgingSettings(BaseModel):
    enabled: bool = True
    density_threshold: float = Field(default=0.10, ge=0.0, le=1.0)
    weight: float = Field(default=0.8, ge=0.0)


class TemplatePhrasesSettings(BaseModel):
    enabled: bool = True
    min_matches: int = Field(default=1, ge=1)
    weight: float = Field(default=1.2, ge=0.0)


class UniformParagraphSettings(BaseModel):
    enabled: bool = True
    min_paragraphs: int = Field(default=3, ge=2)
    length_tolerance: int = Field(default=5, ge=0)
    weight: float = Field(default=0.6, ge=0.0)


class GenericVocabularySettings(BaseModel):
    enabled: bool = True
    density_per_1000: float = Field(default=5.0, ge=0.0)
    weight: float = Field(default=0.7, ge=0.0)


class DetectorSettings(BaseModel):
    TRANSITION_OVERUSE: TransitionOveruseSettings = Field(default_factory=TransitionOveruseSettings)
    SAME_STRUCTURE: SameStructureSettings = Field(default_factory=SameStructureSettings)
    DIRECT_EMOTION: DirectEmotionSettings = Field(default_factory=DirectEmotionSettings)
    HEDGING_PATTERNS: HedgingSettings = Field(default_factory=HedgingSettings)
    TEMPLATE_PHRASES: TemplatePhrasesSettings = Field(default_factory=TemplatePhrasesSettings)
    UNIFORM_PARAGRAPH: UniformParagraphSettings = Field(default_factory=UniformParagraphSettings)
    GENERIC_VOCABULARY: GenericVocabularySettings = Field(default_factory=GenericVocabularySettings)


# ---------------------------------------------------------------------------
# Loop & LLM settings
# ---------------------------------------------------------------------------
class LLMSanityCheckSettings(BaseModel):
    enabled: bool = False
    max_calls_per_chapter: int = Field(default=3, ge=1)
    max_total_tokens: int = Field(default=1000, ge=100)
    chunk_size_chars: int = Field(default=2000, ge=100)
    trigger_below_score: float = Field(default=60.0, ge=0.0, le=100.0)


class LoopSettings(BaseModel):
    max_iterations: int = Field(default=2, ge=1, le=10)
    stop_threshold: float = Field(default=70.0, ge=0.0, le=100.0)
    min_improvement: float = Field(default=2.0, ge=0.0)
    backoff_base_seconds: float = Field(default=0.0, ge=0.0)


class FeatureSettings(BaseModel):
    enabled: bool = True
    default_severity: str = "medium"

    @field_validator("default_severity")
    @classmethod
    def _check_severity(cls, v: str) -> str:
        allowed = {"low", "medium", "high", "critical"}
        if v not in allowed:
            raise ValueError(f"default_severity must be one of {allowed}")
        return v


class AntiAIConfig(BaseModel):
    llm_sanity_check: LLMSanityCheckSettings = Field(default_factory=LLMSanityCheckSettings)
    detectors: DetectorSettings = Field(default_factory=DetectorSettings)
    loop: LoopSettings = Field(default_factory=LoopSettings)
    feature: FeatureSettings = Field(default_factory=FeatureSettings)


# ---------------------------------------------------------------------------
# Loader (YAML -> AntiAIConfig, with env-var overrides)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_yaml(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        logger.warning("anti_ai_config.yaml not found at %s; using defaults", p)
        return {}
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def clear_cache() -> None:
    _load_yaml.cache_clear()


def _apply_env_overrides(cfg: AntiAIConfig) -> AntiAIConfig:
    """Apply env-var overrides on top of the YAML config.

    Env vars:
        ANTI_AI_LLM_ENABLED        -> cfg.llm_sanity_check.enabled
        ANTI_AI_MAX_LOOPS          -> cfg.loop.max_iterations
        ANTI_AI_THRESHOLD          -> cfg.loop.stop_threshold
        ENABLE_ANTI_AI_LOOP        -> cfg.feature.enabled
    """
    if "ANTI_AI_LLM_ENABLED" in os.environ:
        cfg.llm_sanity_check.enabled = os.environ["ANTI_AI_LLM_ENABLED"].lower() in (
            "1", "true", "yes", "on"
        )
    if "ANTI_AI_MAX_LOOPS" in os.environ:
        cfg.loop.max_iterations = int(os.environ["ANTI_AI_MAX_LOOPS"])
    if "ANTI_AI_THRESHOLD" in os.environ:
        cfg.loop.stop_threshold = float(os.environ["ANTI_AI_THRESHOLD"])
    if "ENABLE_ANTI_AI_LOOP" in os.environ:
        cfg.feature.enabled = os.environ["ENABLE_ANTI_AI_LOOP"].lower() in (
            "1", "true", "yes", "on"
        )
    return cfg


def load_anti_ai_config(
    config_path: str | None = None,
    apply_env: bool = True,
) -> AntiAIConfig:
    """Load and validate the anti-AI configuration.

    Args:
        config_path: optional override of the YAML location.
        apply_env: if True (default), apply env-var overrides after
            the YAML is parsed.
    """
    raw = _load_yaml(config_path or str(DEFAULT_CONFIG_PATH))
    cfg = AntiAIConfig(**raw) if raw else AntiAIConfig()
    if apply_env:
        cfg = _apply_env_overrides(cfg)
    return cfg


__all__ = [
    "AntiAIConfig",
    "DetectorSettings",
    "LLMSanityCheckSettings",
    "LoopSettings",
    "FeatureSettings",
    "load_anti_ai_config",
    "clear_cache",
    "DEFAULT_CONFIG_PATH",
]
