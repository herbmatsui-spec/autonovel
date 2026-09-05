"""PublishRecord ORM model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Column, Integer, String, Text, UniqueConstraint, Index
from src.infrastructure.database.models.base_orm import Base


class PublishRecord(Base):
    """投稿履歴レコード"""

    __tablename__ = "publish_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(Integer, nullable=False, index=True)
    episode_num = Column(Integer, nullable=False)
    platform = Column(String(50), nullable=False, index=True)
    post_id = Column(String(255), nullable=False)
    post_url = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="published")
    error_message = Column(Text, nullable=True)
    published_at = Column(Integer, nullable=False)
    updated_at = Column(Integer, nullable=False)

    # ユニーク制約：同一書籍・同一話・同一プラットフォームは1レコード
    __table_args__ = (
        UniqueConstraint(
            "book_id", "episode_num", "platform", name="uq_publish_record_book_ep_platform"
        ),
        Index("ix_publish_record_book_platform", "book_id", "platform"),
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


__all__ = ["PublishRecord"]
