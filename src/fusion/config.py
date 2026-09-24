"""Configuration loader and models for fusion layer."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field


class AnomalyThresholds(BaseModel):
    conflict_spike: float = 2.0
    annotation_stale_episodes: int = 3
    min_avg_confidence: float = 0.6


class FusionConfig(BaseModel):
    source_confidence: Dict[str, float] = Field(
        default_factory=lambda: {
            "annotation": 1.0,
            "rule_engine": 0.8,
            "pipeline": 0.5,
        }
    )
    conflict_threshold: float = 0.3
    significance_threshold: float = 0.3
    blend_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "annotation": 0.7,
            "rule_engine": 0.2,
            "pipeline": 0.1,
        }
    )
    mode: str = "weighted_blend"  # "highest_confidence" | "weighted_blend"
    conflict_penalty: float = 0.2
    alert_channels: List[str] = Field(default_factory=lambda: ["log"])
    webhook_url: str = ""
    anomaly_thresholds: AnomalyThresholds = Field(default_factory=AnomalyThresholds)


_config_instance: Optional[FusionConfig] = None


def reset_fusion_config() -> None:
    """設定インスタンスのリセット（テスト用）"""
    global _config_instance
    _config_instance = None


def load_fusion_config(config_path: Optional[str | Path] = None) -> FusionConfig:
    """融合設定をロードしてシングルトンとして保持する。環境変数オーバーライド対応。"""
    global _config_instance
    if _config_instance is not None and config_path is None:
        return _config_instance

    data: Dict[str, Any] = {}

    if config_path is None:
        default_path = Path("config/fusion.yaml")
        if default_path.exists():
            config_path = default_path

    if config_path:
        path = Path(config_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    data = loaded

    config = FusionConfig(**data)

    # 環境変数オーバーライド
    if "FUSION_CONF_ANNOTATION" in os.environ:
        config.source_confidence["annotation"] = float(os.environ["FUSION_CONF_ANNOTATION"])
    if "FUSION_CONF_RULE_ENGINE" in os.environ:
        config.source_confidence["rule_engine"] = float(os.environ["FUSION_CONF_RULE_ENGINE"])
    if "FUSION_CONF_PIPELINE" in os.environ:
        config.source_confidence["pipeline"] = float(os.environ["FUSION_CONF_PIPELINE"])

    if "FUSION_CONFLICT_THRESHOLD" in os.environ:
        config.conflict_threshold = float(os.environ["FUSION_CONFLICT_THRESHOLD"])
    if "FUSION_SIGNIFICANCE_THRESHOLD" in os.environ:
        config.significance_threshold = float(os.environ["FUSION_SIGNIFICANCE_THRESHOLD"])
    if "FUSION_MODE" in os.environ:
        config.mode = os.environ["FUSION_MODE"]
    if "FUSION_CONFLICT_PENALTY" in os.environ:
        config.conflict_penalty = float(os.environ["FUSION_CONFLICT_PENALTY"])
    if "FUSION_WEBHOOK_URL" in os.environ:
        config.webhook_url = os.environ["FUSION_WEBHOOK_URL"]

    if config_path is None or Path(config_path) == Path("config/fusion.yaml"):
        _config_instance = config

    return config
