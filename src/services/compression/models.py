"""Data models for 4-Layer Context Compression (Step 25)."""
from __future__ import annotations

from typing import Any, Literal
from pathlib import Path
import yaml

from pydantic import BaseModel, Field


SceneType = Literal[
    "general",
    "combat",
    "daily",
    "psychological",
    "political",
    "romance",
    "mystery",
    "flashback",
    "survival",
]


class ProtectedContext(BaseModel):
    """Context elements strictly protected from pruning or compression (Step 52)."""

    active_characters: list[str] = Field(default_factory=list, description="Characters physically present in current scene")
    pending_foreshadowing_ids: list[str] = Field(default_factory=list, description="Foreshadowing IDs awaiting imminent resolution")
    critical_keywords: list[str] = Field(default_factory=list, description="Essential scene intent keywords")
    pinned_entities: set[str] = Field(default_factory=set, description="Entities guaranteed not to be trimmed")


class SudachiConfig(BaseModel):
    """Configuration for SudachiPy tokenizer."""
    split_mode: Literal["A", "B", "C"] = Field(default="C", description="Tokenization mode: A=short, B=medium, C=long")
    include_proper: bool = Field(default=True, description="Include proper nouns")
    include_compound: bool = Field(default=True, description="Include compound nouns")
    min_length: int = Field(default=2, ge=1, description="Minimum token length")
    dict_type: Literal["core", "full", "small"] = Field(default="core", description="Dictionary type")


class CompressionConfig(BaseModel):
    """Configuration for 4-layer context compression."""

    max_tokens: int = Field(default=1500, description="Target maximum token budget for trimmed context")
    target_reduction_ratio: float = Field(default=0.6, description="Target reduction ratio (e.g. 60% reduction)")
    top_keywords: int = Field(default=20, description="Number of top keyphrases to extract in Layer 1")
    max_hops: int = Field(default=2, description="Maximum hops for neighborhood subgraph in Layer 2")
    relevance_threshold: float = Field(default=0.5, description="Minimum relevance score for edge/node pruning")
    scene_type: SceneType = Field(default="general", description="Current scene narrative intent")
    cache_enabled: bool = Field(default=True, description="Whether to enable Redis/in-memory caching")
    cache_ttl_seconds: int = Field(default=3600, description="Cache TTL in seconds")
    preserve_categories: list[str] = Field(
        default_factory=lambda: ["主要キャラ", "核心設定", "伏線"],
        description="Categories that must never be trimmed",
    )
    sudachi: SudachiConfig = Field(default_factory=SudachiConfig, description="SudachiPy tokenizer configuration")


class RawTextLayerOutput(BaseModel):
    """Output of Layer 1: Keyphrase Extraction."""

    extracted_keywords: list[str] = Field(default_factory=list)
    keyword_scores: dict[str, float] = Field(default_factory=dict)
    original_char_count: int = 0
    original_token_count: int = 0


class SubgraphLayerOutput(BaseModel):
    """Output of Layer 2: AGE 2-Hop Subgraph & Edge Pruning."""

    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    seed_entity_names: list[str] = Field(default_factory=list)
    pruned_edge_count: int = 0
    stats: dict[str, Any] = Field(default_factory=dict)


class AbstractionLayerOutput(BaseModel):
    """Output of Layer 3: Conceptual Abstraction & Categorization."""

    abstract_concepts: list[str] = Field(default_factory=list)
    categorized_facts: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    category_mappings: dict[str, list[str]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TrimmedContextOutput(BaseModel):
    """Output of Layer 4: Dynamic Scene-Aware Trimming."""

    compressed_text: str = ""
    token_count: int = 0
    retained_entities: list[str] = Field(default_factory=list)
    reduction_ratio: float = 0.0
    scene_type: SceneType = "general"
    retention_rate: float = 1.0
    pinned_count: int = 0
    dropped_categories: list[str] = Field(default_factory=list)


class CompressedContextResult(BaseModel):
    """Full pipeline execution result."""

    layer1: RawTextLayerOutput | None = None
    layer2: SubgraphLayerOutput | None = None
    layer3: AbstractionLayerOutput | None = None
    layer4: TrimmedContextOutput
    final_context_text: str = ""
    final_token_count: int = 0
    overall_reduction_ratio: float = 0.0
    from_cache: bool = False
    elapsed_ms: float = 0.0
    metrics: CompressionQualityMetrics | None = None

    # --- 旧API互換プロパティ ---
    @property
    def layer1_keyphrases(self) -> list[tuple[str, float]]:
        if not self.layer1:
            return []
        return [(k, self.layer1.keyword_scores.get(k, 1.0)) for k in self.layer1.extracted_keywords]

    @property
    def layer2_subgraph(self) -> dict[str, Any]:
        if not self.layer2:
            return {}
        return {"nodes": self.layer2.nodes, "edges": self.layer2.edges, "stats": self.layer2.stats}

    @property
    def layer3_abstracted(self) -> dict[str, list[dict[str, Any]]]:
        if not self.layer3:
            return {}
        return self.layer3.categorized_facts

    @property
    def layer4_trimmed(self) -> str:
        return self.final_context_text

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "reduction_ratio": self.overall_reduction_ratio,
            "final_tokens": self.final_token_count,
            "elapsed_ms": self.elapsed_ms,
            "from_cache": self.from_cache,
        }


# 旧型エイリアス
CompressionResult = CompressedContextResult


class ReversibleEntityFact(BaseModel):
    """固有名詞と抽象概念を併保持するデュアル表現 (Layer 3)"""
    entity: str = Field(description="元の固有名詞（例：抜刀・迅雷）")
    concept: str = Field(description="一般化された抽象概念（例：雷撃系近接スキル）")
    category: str = Field(description="所属カテゴリ（例：武術・スキル）")
    raw_fact: str = Field(description="抽出元の元テキストまたは属性")
    
    @property
    def display_text(self) -> str:
        """執筆プロンプト用のデュアル表現形式"""
        if self.concept and self.concept != self.entity:
            return f"{self.entity} [{self.concept}]"
        return self.entity


class CompressionQualityMetrics(BaseModel):
    """圧縮品質・情報保持率の定量的評価指標"""
    character_retention_score: float = Field(default=1.0, description="登場人物の保持率 (0.0 - 1.0)")
    foreshadowing_retention_score: float = Field(default=1.0, description="未回収伏線の保持率 (0.0 - 1.0)")
    proper_noun_retention_score: float = Field(default=1.0, description="主要固有名詞の残存率 (0.0 - 1.0)")
    semantic_density_score: float = Field(default=1.0, description="トークンあたりの情報密度スコア")
    overall_consistency_score: float = Field(default=1.0, description="総合整合性スコア (加重平均)")


class SceneFlowHistory(BaseModel):
    """シーン遷移文脈履歴"""
    recent_scene_types: list[SceneType] = Field(default_factory=list, description="直近3〜5話のシーン遷移履歴")
    episode_goal: str = Field(default="", description="本エピソードの主目的（例: 作戦会議・休息・決戦）")
    pacing_tag: str = Field(default="normal", description="テンポ感: setup / confrontation / resolution")


# YAML 設定読み込み関数
_compression_config_instance: CompressionConfig | None = None


def load_compression_config(path: str = "config/context_compression.yaml") -> CompressionConfig:
    config_path = Path(path)
    if not config_path.is_absolute():
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        config_path = project_root / path
    if not config_path.exists():
        return CompressionConfig()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        comp = raw.get("compression", {})
        l1 = comp.get("layer1_keyphrase", {})
        sudachi_cfg = SudachiConfig(**l1.get("sudachi", {})) if "sudachi" in l1 else SudachiConfig()
        return CompressionConfig(
            max_tokens=comp.get("layer4_trimming", {}).get("max_tokens", 1500),
            top_keywords=l1.get("top_k", 20),
            max_hops=comp.get("layer2_subgraph", {}).get("max_hops", 2),
            relevance_threshold=comp.get("layer2_subgraph", {}).get("relevance_threshold", 0.5),
            preserve_categories=comp.get("layer4_trimming", {}).get("preserve_categories", ["主要キャラ", "核心設定", "伏線"]),
            sudachi=sudachi_cfg,
        )
    except Exception:
        return CompressionConfig()


def get_compression_config() -> CompressionConfig:
    global _compression_config_instance
    if _compression_config_instance is None:
        _compression_config_instance = load_compression_config()
    return _compression_config_instance


__all__ = [
    "SceneType",
    "ProtectedContext",
    "SudachiConfig",
    "CompressionConfig",
    "RawTextLayerOutput",
    "SubgraphLayerOutput",
    "AbstractionLayerOutput",
    "TrimmedContextOutput",
    "CompressedContextResult",
    "CompressionResult",
    "load_compression_config",
    "get_compression_config",
    "ReversibleEntityFact",
    "CompressionQualityMetrics",
    "SceneFlowHistory",
]
