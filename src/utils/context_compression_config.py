# src/utils/context_compression_config.py
"""Context Compression 設定読み込みユーティリティ"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, List
import yaml
from pathlib import Path


@dataclass
class Layer1Config:
    """第1層: キーフレーズ抽出設定"""
    method: Literal["tfidf", "keybert", "bm25"]
    top_k: int
    min_score: float


@dataclass
class Layer2Config:
    """第2層: サブグラフ抽出設定"""
    max_hops: int
    relevance_threshold: float
    edge_pruning: bool
    max_nodes: int


@dataclass
class Layer3Config:
    """第3層: 抽象化・カテゴリ化設定"""
    model: str
    max_length: int
    abstraction_categories: List[str]


@dataclass
class Layer4Config:
    """第4層: トリミング設定"""
    importance_threshold: float
    max_tokens: int
    preserve_categories: List[str]


@dataclass
class CompressionConfig:
    """圧縮全体設定"""
    enabled: bool
    layer1: Layer1Config
    layer2: Layer2Config
    layer3: Layer3Config
    layer4: Layer4Config


def load_compression_config(path: str = "config/context_compression.yaml") -> CompressionConfig:
    """設定ファイルを読み込み、型安全な設定オブジェクトを返す"""
    config_path = Path(path)
    if not config_path.is_absolute():
        # プロジェクトルートからの相対パスとして解決
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / path
    
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    
    comp = raw["compression"]
    
    return CompressionConfig(
        enabled=comp["enabled"],
        layer1=Layer1Config(**comp["layer1_keyphrase"]),
        layer2=Layer2Config(**comp["layer2_subgraph"]),
        layer3=Layer3Config(**comp["layer3_abstraction"]),
        layer4=Layer4Config(**comp["layer4_trimming"]),
    )


# シングルトンインスタンス（遅延初期化）
_config_instance: CompressionConfig | None = None


def get_compression_config() -> CompressionConfig:
    """グローバル設定インスタンスを取得（シングルトン）"""
    global _config_instance
    if _config_instance is None:
        _config_instance = load_compression_config()
    return _config_instance