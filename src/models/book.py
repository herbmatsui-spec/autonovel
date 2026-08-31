"""AutoNovel の主要ドメインモデル (Book, Chapter, Character, Plot, Bible)。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base


class Book(Base):
    """作品（シリーズ）のルートモデル。"""

    __tablename__ = "books"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    genre: Mapped[str] = mapped_column(String(100), nullable=False)
    current_branch_id: Mapped[int] = mapped_column(Integer, default=1)

    chapters: Mapped[list[Chapter]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    characters: Mapped[list[Character]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    plots: Mapped[list[Plot]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    bibles: Mapped[list[Bible]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )


class Chapter(Base):
    """各話（本文）モデル。is_anchor=True は固定_anchor 章として扱う。"""

    __tablename__ = "chapters"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    ep_num: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_anchor: Mapped[bool] = mapped_column(default=False)

    book: Mapped[Book] = relationship(back_populates="chapters")


class Character(Base):
    """キャラクター設定モデル。"""

    __tablename__ = "characters"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)


    role: Mapped[str] = mapped_column(String(100), nullable=True)
    personality: Mapped[str] = mapped_column(Text, nullable=True)
    ability: Mapped[str] = mapped_column(Text, nullable=True)

    book: Mapped[Book] = relationship(back_populates="characters")


class Plot(Base):
    """プロット概要モデル。分岐 (branch_id) を持つ。"""

    __tablename__ = "plots"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    branch_id: Mapped[int] = mapped_column(Integer, default=1)
    ep_num: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    one_line_summary: Mapped[str] = mapped_column(Text, nullable=False)

    book: Mapped[Book] = relationship(back_populates="plots")


class Bible(Base):
    """世界観設定（JSON 文字列として保存）。"""

    __tablename__ = "bibles"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    settings: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)  # Unix timestamp

    book: Mapped[Book] = relationship(back_populates="bibles")
