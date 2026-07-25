from __future__ import annotations
from typing import Any, Dict, List, Optional
from src.backend.database.repo_protocols import IRepository

class InMemoryRepository(IRepository):
    """
    テストおよび開発用のインメモリリポジトリ。
    SQLAlchemyへの依存を排除し、高速なテスト実行を可能にする。
    """
    def __init__(self):
        self.books: Dict[str, Any] = {}
        self.plots: Dict[str, Any] = {}
        self.chapters: Dict[str, Any] = {}
        self.characters: Dict[str, Any] = {}
        self.bible: Dict[str, Any] = {}
        self.misc: Dict[str, Any] = {}

    async def update_plot_blueprint(self, book_id: str, blueprint: Any) -> bool:
        if book_id not in self.plots:
            self.plots[book_id] = {}
        self.plots[book_id]["blueprint"] = blueprint
        return True

    async def create_book(self, book_data: Any) -> str:
        book_id = book_data.get("id") or str(len(self.books) + 1)
        self.books[book_id] = book_data
        return book_id

    async def save_plot(self, plot_data: Any) -> bool:
        book_id = plot_data.get("book_id")
        if not book_id:
            return False
        if book_id not in self.plots:
            self.plots[book_id] = {}
        self.plots[book_id].update(plot_data)
        return True
