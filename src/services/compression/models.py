"""Data models for 4-Layer Context Compression (Step 25)."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


SceneType = Literal["general", "combat", "daily", "psychological", "political"]


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


class TrimmedContextOutput(BaseModel):
    """Output of Layer 4: Dynamic Scene-Aware Trimming."""

    compressed_text: str = ""
    token_count: int = 0
    retained_entities: list[str] = Field(default_factory=list)
    reduction_ratio: float = 0.0
    scene_type: SceneType = "general"


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


__all__ = [
    "SceneType",
    "CompressionConfig",
    "RawTextLayerOutput",
    "SubgraphLayerOutput",
    "AbstractionLayerOutput",
    "TrimmedContextOutput",
    "CompressedContextResult",
]
