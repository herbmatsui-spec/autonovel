import asyncio
import logging
from typing import Any, Dict, List, Optional

from src.core.observability import StructuredLogger, TraceContext

logger = logging.getLogger(__name__)

class StreamingPlotScheduler:
    """エピソードのプロット生成をストリーミングスケジュール管理する"""
    def __init__(self, repo: Any, llm: Any, pm: "IPromptManager", planner: Any, book_id: int, branch_id: int, arcs: List[Any], end_ep: int, reporter=None):
        self.repo = repo
        self.llm = llm
        self.pm = pm
        self.planner = planner
        self.book_id = book_id
        self.branch_id = branch_id
        self.arcs = arcs
        self.end_ep = end_ep
        self.reporter = reporter
        self.tasks = {}

    async def schedule_plot_generation(self, ep_num: int, bible: Any, settings: Dict[str, Any]):
        if ep_num > self.end_ep:
            return
        if ep_num in self.tasks:
            return

        async def _run_gen():
            try:
                # 既にプロットが存在するか確認
                plot = await self.repo.get_plot(self.branch_id, ep_num)
                if plot and plot.detailed_blueprint and len(plot.detailed_blueprint) > 50:
                    return plot

                if self.reporter:
                    self.reporter.report(f"🗺️ プロット先行生成スケジュール: 第{ep_num}話", "info")

                results = await self.planner.expand_plots(self.book_id, [ep_num], self.arcs, reporter=self.reporter)
                if results:
                    return results[0]
            except Exception as e:
                StructuredLogger.error("Failed scheduled plot gen", trace_id=TraceContext.get_trace_id(), error=e)
                return None

        self.tasks[ep_num] = asyncio.create_task(_run_gen())

    async def await_plot_ready(self, ep_num: int) -> Optional[Any]:
        if ep_num not in self.tasks:
            return await self.repo.get_plot(self.branch_id, ep_num)
        task = self.tasks[ep_num]
        return await task

