"""Four-Layer Context Compression Package."""
from __future__ import annotations

from src.services.compression.models import (
    SceneType,
    CompressionConfig,
    RawTextLayerOutput,
    SubgraphLayerOutput,
    AbstractionLayerOutput,
    TrimmedContextOutput,
    CompressedContextResult,
)
from src.services.compression.layer1_keywords import (
    Layer1KeywordExtractor,
    extract_keyphrases,
    count_tokens,
)
from src.services.compression.layer2_subgraph import (
    Layer2SubgraphExtractor,
    RELATION_WEIGHTS,
)
from src.services.compression.layer3_abstraction import (
    Layer3ConceptAbstractor,
    DEFAULT_CATEGORIES,
    CONCEPT_TAXONOMY,
)
from src.services.compression.layer4_trimming import (
    Layer4SceneTrimmer,
    SCENE_CATEGORY_WEIGHTS,
)
from src.services.compression.cache import CompressionCache
from src.services.compression.compressor import FourLayerCompressor

__all__ = [
    "SceneType",
    "CompressionConfig",
    "RawTextLayerOutput",
    "SubgraphLayerOutput",
    "AbstractionLayerOutput",
    "TrimmedContextOutput",
    "CompressedContextResult",
    "Layer1KeywordExtractor",
    "extract_keyphrases",
    "count_tokens",
    "Layer2SubgraphExtractor",
    "RELATION_WEIGHTS",
    "Layer3ConceptAbstractor",
    "DEFAULT_CATEGORIES",
    "CONCEPT_TAXONOMY",
    "Layer4SceneTrimmer",
    "SCENE_CATEGORY_WEIGHTS",
    "CompressionCache",
    "FourLayerCompressor",
]
