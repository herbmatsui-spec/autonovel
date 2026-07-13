# agents/base.py
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """すべてのエージェントの基底クラス"""
    def __init__(self, repo: Any = None, llm: Any = None, style_rag: Any = None, rag_prefetch: Any = None):
        self.repo = repo
        self.llm = llm
        self.style_rag = style_rag
        self.rag_prefetch = rag_prefetch

    def _safe_get_dict(self, data: Any) -> Dict[str, Any]:
        """データを安全に辞書に変換するユーティリティ"""
        import json
        if not data:
            return {}
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            try:
                return json.loads(data)
            except Exception:
                return {}
        return {}

    def _safe_get_list(self, data: Any) -> list:
        """データを安全にリストに変換するユーティリティ"""
        import json
        if not data:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, str):
            try:
                res = json.loads(data)
                return res if isinstance(res, list) else []
            except Exception:
                return []
        return []

    async def _get_book_branch(self, book_id: int) -> int:
        """本の現在のブランチIDを安全に取得する"""
        book = await self.repo.get_book(book_id)
        return book.current_branch_id if book and book.current_branch_id else 1

    @abstractmethod
    async def run(self, *args, **kwargs):
        """エージェント固有のメインロジック。サブクラスで実装する。"""
        pass

