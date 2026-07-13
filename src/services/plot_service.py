from typing import Any, List, Optional

from src.core.interfaces import IRepository


class PlotService:
    """プロット管理サービス"""
    def __init__(self, repo: IRepository):
        self.repo = repo

    async def get_plot(self, book_id: int, ep_num: int) -> Optional[Any]:
        return await self.repo.get_plot(book_id, ep_num)

    async def get_plots_between(self, book_id: int, start_ep: int, end_ep: int) -> List[Any]:
        return await self.repo.get_plots_between(book_id, start_ep, end_ep)

    async def update_plot_blueprint(self, branch_id: int, ep_num: int, blueprint: str) -> None:
        await self.repo.update_plot_blueprint(branch_id, ep_num, blueprint)
