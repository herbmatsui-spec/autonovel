"""Task ORM model."""
from __future__ import annotations

from typing import Any
from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base_orm import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    result: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


__all__ = ["Task"]
