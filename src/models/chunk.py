"""章チャンク・ベクトル表現データモデル."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.types import JSON, TypeDecorator

from src.models.base import Base

# pgvector が利用可能な場合は Vector をインポート、ない場合は JSON/配列フォールバック
try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False
    class Vector(TypeDecorator):  # type: ignore
        """pgvector がない環境 (SQLite 等) 用のダミー型デコレータ."""
        impl = JSON
        cache_ok = True

        def process_bind_param(self, value: Any, dialect: Any) -> Any:
            return value

        def process_result_value(self, value: Any, dialect: Any) -> Any:
            return value


class ChapterChunk(Base):
    """小説本文の段落・シーンチャンクおよびベクトル埋め込みモデル."""

    __tablename__ = "chapter_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=False)

    # 1536次元 (OpenAI text-embedding-3-small / ada-002 等)
    embedding = Column(Vector(1536), nullable=True)

    # 抽出エンティティやメタ情報 (JSON / JSONB)
    chunk_metadata = Column(JSON, nullable=True, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<ChapterChunk(id={self.id}, chapter_id={self.chapter_id}, index={self.chunk_index})>"
