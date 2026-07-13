"""
engine.py - 覇権AIエンジンコアモジュール
Gemini API との対話、プロット生成、本文執筆の全ロジックを集約。
UltimateHegemonyEngine が全機能を統合する。
"""
from __future__ import annotations

import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# サブモジュールと定数のインポート
from src.backend.tension_utils import calculate_progress, get_target_tension, select_tension_curve


# ==========================================
# UltimateHegemonyEngine（メインエンジン）
# ==========================================
class UltimateHegemonyEngine:
    """覇権小説自動生成エンジン v2.0"""

    def __init__(
        self,
        api_key: str,
        planner,
        writer,
        repo,
        db,
        pm,
        ctx_mgr,
        formatter,
        validator,
        auditor,
        narrative,
        critique,
        marketing,
        bible_agent,
        plot_agent,
        style_rag,
        llm,
        cooldown
    ):
        self.api_key = api_key
        self.planner = bible_agent
        self.planning_agent = planner
        self.writer = writer
        self.repo = repo
        self.db = db
        self.pm = pm
        self.ctx_mgr = ctx_mgr
        self.formatter = formatter
        self.validator = validator
        self.auditor = auditor
        self.narrative = narrative
        self.critique = critique
        self.marketing = marketing
        self.bible_agent = bible_agent
        self.plot_agent = plot_agent
        self.style_rag = style_rag
        self.llm = llm
        self.cooldown = cooldown

        # 後方互換性用のエイリアス
        self.ai_api = llm
        self.llm_client = llm
        self.client = None
        self.current_ep_num = 0



    async def sync_bible(self, book_id: int, reporter=None):

        """
        Bibleのライフサイクル同期（承認済み設定のマージ -> 最適化 -> 整合性監査）を実行する。
        """
        return await self.bible_agent.sync_bible_lifecycle(book_id, reporter=reporter)

    async def resolve_bible_setting(self, setting_id: int, status: str):
        """
        仮設定のステータスを更新する（承認/却下）。
        """
        await self.repo.resolve_pending_setting(setting_id, status)

    async def determine_target_tension(self, book_id: int, ep_num: int, genre: str, story_type: Optional[str] = None) -> float:
        """
        現在の進行度とジャンルに基づき、このエピソードが到達すべき目標Tension値を計算し、DBに保存する。
        """
        # 1. 曲線選択
        curve_name = select_tension_curve(genre, story_type)

        # 2. 全エピソード数の取得
        total_episodes = await self.repo.get_total_episodes(book_id)
        if total_episodes == 0:
            return 0.0

        # 3. 進行度計算と目標値算出
        progress = calculate_progress(ep_num, total_episodes)
        target_val = get_target_tension(curve_name, progress)

        # 4. DBに保存 (後続のプロンプト注入で使用するため)
        # PlotDbModelのtarget_tensionカラムを更新
        await self.repo.update_plot_target_tension(book_id, ep_num, target_val)

        return target_val

    async def validate_tension_deviation(self, ep_num: int, generated_tension: float, book_id: int, tolerance: float = 0.2) -> Tuple[bool, float]:
        """
        生成されたtension値が目標値から許容範囲内にあるか検証する。
        returns: (is_valid, deviation)
        """
        # DBから目標値を取得
        plot = await self.repo.get_plot(book_id_or_branch_id=book_id, ep_num=ep_num)
        if not plot or plot.target_tension is None:
            return True, 0.0

        target = plot.target_tension
        deviation = abs(generated_tension - target)

        is_valid = deviation <= tolerance
        return is_valid, deviation

