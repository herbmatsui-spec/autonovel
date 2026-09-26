"""NanoBanana 2 Lite Manga Pipeline package（1話1枚・24コマ一括生成）。

.. deprecated::
   本パッケージの `quality_gate` / `upscaler` / `typesetter` は統合
   イラスト生成エンジン（`src/services/illustration/`）へ委譲する薄い
   互換 shim になった。新たなコードは
   `src.services.illustration.unified_generator` を使用すること。
   `MangaPipeline` は「1話1枚」の専用パイプラインとして当面温存する。
"""
from src.services.manga.config import MangaPipelineConfig
from src.services.manga.models import (
    AspectRatio,
    CharacterReference,
    MangaEpisodeInput,
    MangaPipelineResult,
    QualityCheckResult,
    SpeechBubble,
)
from src.services.manga.pipeline import MangaPipeline
from src.services.manga.prompt_generator import MangaPromptGenerator
from src.services.manga.quality_gate import MangaQualityGate
from src.services.manga.typesetter import MangaTypesetter
from src.services.manga.upscaler import MangaUpscaler

__all__ = [
    "AspectRatio",
    "CharacterReference",
    "MangaEpisodeInput",
    "MangaPipeline",
    "MangaPipelineConfig",
    "MangaPipelineResult",
    "MangaPromptGenerator",
    "MangaQualityGate",
    "MangaTypesetter",
    "MangaUpscaler",
    "QualityCheckResult",
    "SpeechBubble",
]
