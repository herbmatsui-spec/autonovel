"""
scheduler_coordinator.py - ストリーミングスケジューラ連携

EpisodePipeline からスケジューラのライフサイクル管理（初期化・プロット待機・
先行生成スケジューリング・キャンセル・GraphManager への注入）を分離する。
"""

from __future__ import annotations

import json
from typing import Any, List, Optional


class SchedulerCoordinator:
    """StreamingPlotScheduler のライフサイクルを管理するコーディネーター"""

    def __init__(self, agent: Any):
        self.agent = agent
        self.scheduler = None

    async def _load_arcs(self, book_id: int) -> List[Any]:
        arcs: List[Any] = []
        try:
            bible = await self.agent._get_bible(book_id)
            if bible:
                settings = {}
                if hasattr(bible, "world_settings") and bible.world_settings:
                    settings = bible.world_settings
                elif hasattr(bible, "settings") and bible.settings:
                    if isinstance(bible.settings, str):
                        try:
                            settings = json.loads(bible.settings)
                        except Exception:
                            settings = {}
                    elif isinstance(bible.settings, dict):
                        settings = bible.settings
                arcs = settings.get("arcs", []) if isinstance(settings, dict) else []
        except Exception as e:
            if hasattr(self.agent, 'logger'):
                self.agent.logger.debug(f"Failed to get arcs for book_id={book_id}: {e}")
        return arcs

    def initialize(
        self,
        book_id: int,
        end_ep: int,
        arcs: List[Any],
        reporter: Any,
        branch_id: int = 1,
    ) -> bool:
        """StreamingPlotScheduler を初期化する。成功時 True。"""
        if getattr(self.agent, 'plot_expander', None) is None or not arcs:
            return False
        try:
            from src.agents.writing_scheduler import StreamingPlotScheduler

            self.scheduler = StreamingPlotScheduler(
                repo=getattr(self.agent, 'repo', None),
                llm=getattr(self.agent, 'llm', None),
                pm=getattr(self.agent, 'prompt_manager', None),
                planner=getattr(self.agent, 'plot_expander', None),
                book_id=book_id,
                branch_id=getattr(self.agent, 'branch_id', branch_id),
                arcs=arcs,
                end_ep=end_ep,
                reporter=reporter,
            )
            if reporter:
                reporter.report(f"プロット先行スケジューラを起動 (arcs={len(arcs)})", "info")
        except Exception as e:
            if hasattr(self.agent, 'logger'):
                self.agent.logger.warning(f"Failed to initialize StreamingPlotScheduler: {e}")
            self.scheduler = None
            return False

        try:
            self._attach_to_graph_manager()
        except Exception as e:
            if hasattr(self.agent, 'logger'):
                self.agent.logger.debug(f"Skipping graph manager scheduler attach: {e}")
        return True

    def _attach_to_graph_manager(self) -> None:
        if self.scheduler is None:
            return
        graph_manager = getattr(self.agent, "_writing_graph_manager", None)
        if graph_manager is not None and hasattr(graph_manager, "set_scheduler"):
            graph_manager.set_scheduler(self.scheduler)

    async def await_ready(self, ep: int) -> None:
        if self.scheduler is None:
            return
        try:
            await self.scheduler.await_plot_ready(ep)
        except Exception as e:
            if hasattr(self.agent, 'logger'):
                self.agent.logger.warning(f"Scheduler await failed for Ep.{ep}: {e}")

    def schedule_ahead(self, ep: int, end_ep: int) -> None:
        if self.scheduler is None:
            return
        try:
            if ep + 1 <= end_ep:
                self.scheduler.schedule_plot_generation(ep + 1, None, {})
            if ep + 2 <= end_ep:
                self.scheduler.schedule_plot_generation(ep + 2, None, {})
        except Exception as e:
            if hasattr(self.agent, 'logger'):
                self.agent.logger.warning(f"Scheduler schedule failed for Ep.{ep}: {e}")

    def cancel_all(self) -> None:
        if self.scheduler is None:
            return
        try:
            for task in self.scheduler.tasks.values():
                if not task.done():
                    task.cancel()
        except Exception as exc:
            if hasattr(self.agent, 'logger'):
                self.agent.logger.warning("スケジューラタスクのキャンセルに失敗: %s", exc, exc_info=True)
