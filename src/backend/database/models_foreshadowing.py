"""ForeshadowingModel - 伏線ステートマシン SQLAlchemy ORMモデル。

伏線の設置・進展・回収・放棄をリレーショナルテーブルで管理する。
Apache AGE / NetworkX を完全に置換するv5.0の中核テーブル。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from src.infrastructure.database.models.base_orm import Base


class ForeshadowingModel(Base):
    """伏線ステートマシンモデル。

    Attributes:
        id: 伏線の一意識別子
        book_id: 所属作品ID（booksテーブル外部キー）
        title: 伏線タイトル（例: 「謎の剣」「消えた手紙」）
        description: 伏線の内容説明
        planted_episode: 伏線を設置した話数
        target_episode: 回収目標話数（NULL許容：作者に委ねる場合）
        resolved_episode: 実際に回収された話数（NULL = 未回収）
        scope: 伏線のスコープ (short_term / long_term)
        status: 伏線の現在ステータス (planted / progressed / resolved / abandoned)
        created_at: レコード作成日時
        updated_at: レコード更新日時
    """

    __tablename__ = "foreshadowings"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(
        Integer,
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    planted_episode = Column(Integer, nullable=False)
    target_episode = Column(Integer, nullable=True)
    resolved_episode = Column(Integer, nullable=True)
    scope = Column(String(32), nullable=False, server_default='short_term')
    status = Column(String(20), default="planted", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Foreshadowing(id={self.id}, title='{self.title}', "
            f"status='{self.status}', planted_ep={self.planted_episode})>"
        )
