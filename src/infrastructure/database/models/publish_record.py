"""PublishRecord ORM model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Integer, String, Text, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base_orm import Base


class PublishRecord(Base):
    """投稿履歴レコード"""

    __tablename__ = "publish_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    episode_num: Mapped[int] = mapped_column(Integer, nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    post_id: Mapped[str] = mapped_column(String(255), nullable=False)
    post_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="published")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

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
