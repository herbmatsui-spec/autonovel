"""AutoNovel ドメインモデル集約エクスポート."""

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

from .book import Bible, Book, Chapter, Character, Plot  # noqa: E402
from .task import Task  # noqa: E402

__all__ = [
    "Base",
    "Bible",
    "Book",
    "Chapter",
    "Character",
    "Plot",
    "Task",
]
