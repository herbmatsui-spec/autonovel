"""
episode_pipeline.py - エピソード生成パイプライン
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.agents.scheduler_coordinator import SchedulerCoordinator
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
            tuple[total_chars, failed_episodes]
        """
        total_chars = 0
        failed_episodes: List[Dict[str, Any]] = []

        coordinator = SchedulerCoordinator(self)
        arcs = await coordinator._load_arcs(book_id)
        coordinator.initialize(book_id, end_ep, arcs, reporter, branch_id)

        for ep in range(start_ep, end_ep + 1):
            try:
                if coordinator.scheduler is not None:
                    await coordinator.await_ready(ep)
                    coordinator.schedule_ahead(ep, end_ep)

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

        coordinator.cancel_all()
        return total_chars, failed_episodes
