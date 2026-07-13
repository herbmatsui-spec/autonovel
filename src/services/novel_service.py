from typing import Any, Dict, List, Optional

from src.core.interfaces import IRepository


class NovelService:
    """小説全体管理サービス"""
    def __init__(self, repo: IRepository):
        self.repo = repo

    async def get_chapter(self, branch_id: int, ep_num: int) -> Optional[Any]:
        return await self.repo.get_chapter(branch_id, ep_num)

    async def get_all_non_anchor_chapters(self, book_id: int) -> List[Any]:
        return await self.repo.get_all_non_anchor_chapters(book_id)

    async def create_book(self, title: str, genre: str, target_eps: int) -> Dict[str, Any]:
        return await self.repo.create_book(title=title, genre=genre, target_eps=target_eps)
