"""章チャンクモデル（後方互換 re-export）."""
from src.infrastructure.database.models.chunk import HAS_PGVECTOR, ChapterChunk, Vector

__all__ = ["ChapterChunk", "Vector", "HAS_PGVECTOR"]
