"""章チャンクモデル（後方互換 re-export）."""
from src.infrastructure.database.models.chunk import ChapterChunk, Vector, HAS_PGVECTOR

__all__ = ["ChapterChunk", "Vector", "HAS_PGVECTOR"]
