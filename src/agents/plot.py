import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Optional

from src.agents.base import BaseAgent

if TYPE_CHECKING:
    from src.core.interfaces import IPlotExpander, IPromptManager, IReporter, IRepository
    from src.models import Arc, PlotDetail

logger = logging.getLogger(__name__)


class PlotAgent(BaseAgent):
    """プロット設計、アーク分割などを担当"""
    def __init__(
        self,
        repo: "IRepository",
        pm: "IPromptManager",
        generate_json: Callable[..., Awaitable[Any]],
        plot_expander: Optional["IPlotExpander"] = None
    ):
        super().__init__()
        self.repo = repo
        self.pm = pm
        self.generate_json = generate_json
        self._plot_expander = plot_expander

    def _ensure_services(self):
        if self._plot_expander is None:
            raise RuntimeError("Services are not injected. Please provide plot_expander.")

    async def expand_plots(
        self, book_id: int, ep_nums: List[int], arcs: List["Arc"],
        reporter: Optional["IReporter"] = None, force: bool = False, branch_id: Optional[int] = None,
    ) -> List["PlotDetail"]:
        """各エピソードのプロット詳細を展開する（実際のLLM呼び出し）"""
        self._ensure_services()

        if reporter:
            reporter.report(f"プロット展開を開始します... (対象話数: {ep_nums})", "info")

        results = await self._plot_expander.expand_plots(
            book_id=book_id,
            target_ep_list=ep_nums,
            arcs=arcs,
            reporter=reporter,
            force=force,
            branch_id=branch_id,
        )
        return results

    async def rebuild_hegemony_plot(
        self, book_id: int, start_ep: int, new_total_eps: int, keywords: str,
        trend_memo: str, plot_pattern_key: str, cost_severity: int, cheat_scale: int,
        system_assist: int, reporter=None
    ) -> List[Any]:
        """
        第X話以降のプロット再構築機能を実行する。

        Args:
            book_id: 書籍ID
            start_ep: 再構築開始話数
            new_total_eps: 新しい総話数
            keywords: キーワード
            trend_memo: トレンドメモ
            plot_pattern_key: プロットパターンキー
            cost_severity: コスト重要度
            cheat_scale: チートスケール
            system_assist: システムアシスト値
            reporter: 進捗レポーター

        Returns:
            再構築されたプロットのリスト（現在未実装のため空リストを返す）

        .. note::
            このメソッドは現在未実装です。ステップ16-22のPlotAgent実装計画で検討されます。
        """
        import warnings
        warnings.warn(
            f"rebuild_hegemony_plot は現在未実装です。"
            f"第{start_ep}話以降のプロット再構築は現在のところサポートされていません。",
            UserWarning,
            stacklevel=2
        )
        if reporter:
            reporter.report(f"第{start_ep}話以降のプロット再構築を開始します...", "info")
        # 現在未実装のため空のリストを返す
        return []

    async def run(self, *args, **kwargs):
        logger.info("PlotAgent run invoked")
        return await self.expand_plots(**kwargs)

