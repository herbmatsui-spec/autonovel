"""
src/backend/plot_service.py - プロット生成・テンション管理サービス。

UltimateHegemonyEngine からテンション関連責務を分離したドメインサービス。
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PlotService:
    """プロット生成・テンション管理を担当するドメインサービス。"""

    def __init__(self, repo, llm=None):
        self.repo = repo
        self.llm = llm

    async def determine_target_tension(
        self,
        book_id: int,
        ep_num: int,
        genre: str,
        story_type: Optional[str] = None,
    ) -> float:
        """
        現在の進行度とジャンルに基づき、このエピソードが到達すべき目標Tension値を計算し、DBに保存する。
        """
        from src.backend.tension_utils import calculate_progress, get_target_tension, select_tension_curve

        curve_name = select_tension_curve(genre, story_type)

        total_episodes = await self.repo.get_total_episodes(book_id)
        if total_episodes == 0:
            return 0.0

        progress = calculate_progress(ep_num, total_episodes)
        target_val = get_target_tension(curve_name, progress)

        await self.repo.update_plot_target_tension(book_id, ep_num, target_val)

        return target_val

    async def validate_tension_deviation(
        self,
        ep_num: int,
        generated_tension: float,
        book_id: int,
        tolerance: float = 0.2,
    ) -> tuple[bool, float]:
        """
        生成されたtension値が目標値から許容範囲内にあるか検証する。
        returns: (is_valid, deviation)
        """
        plot = await self.repo.get_plot(book_id_or_branch_id=book_id, ep_num=ep_num)
        if not plot or plot.target_tension is None:
            return True, 0.0

        target = plot.target_tension
        deviation = abs(generated_tension - target)

        is_valid = deviation <= tolerance
        return is_valid, deviation
