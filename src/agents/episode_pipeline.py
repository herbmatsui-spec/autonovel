"""
episode_pipeline.py - エピソード生成パイプライン
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from src.agents.writing_scheduler import StreamingPlotScheduler
from src.agents.base import BaseAgent


class EpisodePipeline:
    """エピソード生成パイプラインを管理するクラス"""

    def __init__(self, agent: Any):
        """
        Args:
            agent: 親エージェント（WritingAgent インスタンス）
        """
        self.agent = agent

    async def run(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float,
        target_word_count: int,
        is_easy_mode: bool,
        reporter: Any,
        branch_id: int = 1,
        style_tag: Optional[str] = None,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """エピソード生成パイプラインを実行する。

        Returns:
            tuple[total_chars, failed_episodes] where:
                total_chars: 生成された総文字数
                failed_episodes: 失敗したエピソードのリスト
        """
        total_chars = 0
        failed_episodes: List[Dict[str, Any]] = []

        scheduler = None
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

        if getattr(self.agent, 'plot_expander', None) is not None and arcs:
            try:
                scheduler = StreamingPlotScheduler(
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
                scheduler = None

            try:
                self._attach_scheduler_to_graph_manager(scheduler)
            except Exception as e:
                if hasattr(self.agent, 'logger'):
                    self.agent.logger.debug(f"Skipping graph manager scheduler attach: {e}")

        for ep in range(start_ep, end_ep + 1):
            try:
                if scheduler is not None:
                    try:
                        await scheduler.await_plot_ready(ep)
                    except Exception as e:
                        if hasattr(self.agent, 'logger'):
                            self.agent.logger.warning(f"Scheduler await failed for Ep.{ep}: {e}")

                    if ep + 1 <= end_ep:
                        scheduler.schedule_plot_generation(ep + 1, None, {})
                    if ep + 2 <= end_ep:
                        scheduler.schedule_plot_generation(ep + 2, None, {})

                chars = await self.agent.generate_episodes(
                    book_id=book_id,
                    start_ep=ep,
                    end_ep=ep,
                    passion=passion,
                    target_word_count=target_word_count,
                    is_easy_mode=is_easy_mode,
                    reporter=reporter,
                    branch_id=branch_id,
                    style_tag=style_tag,
                )
                if chars > 0:
                    total_chars += chars
                else:
                    failed_episodes.append({"ep_num": ep, "error_message": "0文字生成"})
            except Exception as e:
                if hasattr(self.agent, 'logger'):
                    self.agent.logger.error(f"generate_episodes_pipeline failed at ep {ep}: {e}")
                failed_episodes.append({"ep_num": ep, "error_message": str(e)})

        if scheduler is not None:
            try:
                for task in scheduler.tasks.values():
                    if not task.done():
                        task.cancel()
            except Exception as exc:
                if hasattr(self.agent, 'logger'):
                    self.agent.logger.warning("スケジューラタスクのキャンセルに失敗: %s", exc, exc_info=True)

        return total_chars, failed_episodes

    def _attach_scheduler_to_graph_manager(self, scheduler) -> None:
        """StreamingPlotScheduler を WritingGraphManager に注入する（存在する場合のみ）"""
        if scheduler is None:
            return
        graph_manager = getattr(self.agent, "_writing_graph_manager", None)
        if graph_manager is not None and hasattr(graph_manager, "set_scheduler"):
            graph_manager.set_scheduler(scheduler)
