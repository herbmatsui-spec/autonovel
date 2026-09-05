# src/utils/phase3_config.py
"""Phase 3 共通設定読み込みユーティリティ"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from pathlib import Path
import yaml


@dataclass
class FeaturesConfig:
    """機能フラグ設定"""
    compression_enabled: bool
    dag_scheduler_enabled: bool
    social_interaction_enabled: bool


@dataclass
class ResourcesConfig:
    """リソース制限設定"""
    max_cpu_cores: int
    max_memory_gb: int
    max_gpu_memory_gb: int
    max_gpu_count: int


@dataclass
class LoggingConfig:
    """ログ設定"""
    level: str
    format: str
    phase_prefix: str


@dataclass
class MetricsConfig:
    """メトリクス設定"""
    prefix: str
    default_buckets: dict


@dataclass
class CacheConfig:
    """キャッシュ設定"""
    redis_url: str
    default_ttl_seconds: int
    compression_cache_prefix: str
    dag_cache_prefix: str
    social_cache_prefix: str


@dataclass
class TimeoutsConfig:
    """タイムアウト設定"""
    default_task_timeout_seconds: int
    dag_task_timeout_seconds: int
    compression_timeout_seconds: int
    social_generation_timeout_seconds: int
    llm_request_timeout_seconds: int


@dataclass
class RetryConfig:
    """リトライ設定"""
    max_retries: int
    base_delay_seconds: float
    max_delay_seconds: float
    exponential_base: float


@dataclass
class CircuitBreakerConfig:
    """サーキットブレーカー設定"""
    failure_threshold: int
    recovery_timeout_seconds: int
    half_open_max_calls: int


@dataclass
class Phase3Config:
    """Phase 3 全体設定"""
    features: FeaturesConfig
    resources: ResourcesConfig
    logging: LoggingConfig
    metrics: MetricsConfig
    cache: CacheConfig
    timeouts: TimeoutsConfig
    retry: RetryConfig
    circuit_breaker: CircuitBreakerConfig


def load_phase3_config(path: str = "config/phase3_common.yaml") -> Phase3Config:
    """設定ファイルを読み込み、型安全な設定オブジェクトを返す"""
    config_path = Path(path)
    if not config_path.is_absolute():
        # プロジェクトルートからの相対パスとして解決
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / path

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return Phase3Config(
        features=FeaturesConfig(**raw["features"]),
        resources=ResourcesConfig(**raw["resources"]),
        logging=LoggingConfig(**raw["logging"]),
        metrics=MetricsConfig(**raw["metrics"]),
        cache=CacheConfig(**raw["cache"]),
        timeouts=TimeoutsConfig(**raw["timeouts"]),
        retry=RetryConfig(**raw["retry"]),
        circuit_breaker=CircuitBreakerConfig(**raw["circuit_breaker"]),
    )


# シングルトンインスタンス（遅延初期化）
_config_instance: Phase3Config | None = None


def get_phase3_config() -> Phase3Config:
    """グローバル設定インスタンスを取得（シングルトン）"""
    global _config_instance
    if _config_instance is None:
        _config_instance = load_phase3_config()
    return _config_instance