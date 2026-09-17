"""EpisodeDigestModel - 100字事実ダイジェスト SQLAlchemy ORMモデル。

各話執筆完了時に生成される客観的事実ダイジェスト（最大150字）を保存する。
3層ローリング記憶の中核として、コンテキスト窓の肥大化を防ぎつつ
長期のストーリー整合性を維持する。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text

from src.infrastructure.database.models.base_orm import Base


class EpisodeDigestModel(Base):
    """エピソード確定事実ダイジェストモデル。

    Attributes:
        id: ダイジェストの一意識別子
        book_id: 所属作品ID（booksテーブル外部キー）
        episode_num: 話数
        digest_text: 確定した客観的事実の要約テキスト（最大150字）
        created_at: レコード作成日時
        updated_at: レコード更新日時
    """

    __tablename__ = "episode_digests"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    episode_num = Column(Integer, nullable=False, index=True)
    digest_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<EpisodeDigest(id={self.id}, book_id={self.book_id}, "
            f"ep={self.episode_num}, digest='{self.digest_text[:20]}...')>"
        )
