"""
engine.py - 覇権AIエンジンコアモジュール
Gemini API との対話、プロット生成、本文執筆の全ロジックを集約。
UltimateHegemonyEngine が全機能を統合する。
"""

from __future__ import annotations

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


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
        cooldown,
        plot_service,
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
        self.plot_service = plot_service

    @property
    def ai_api(self):
        import warnings

        warnings.warn(
            "ai_api is deprecated, use llm instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.llm

    @property
    def llm_client(self):
        import warnings

        warnings.warn(
            "llm_client is deprecated, use llm instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.llm

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

    async def determine_target_tension(
        self, book_id: int, ep_num: int, genre: str, story_type: Optional[str] = None
    ) -> float:
        return await self.plot_service.determine_target_tension(
            book_id=book_id, ep_num=ep_num, genre=genre, story_type=story_type
        )

    async def validate_tension_deviation(
        self, ep_num: int, generated_tension: float, book_id: int, tolerance: float = 0.2
    ) -> Tuple[bool, float]:
        return await self.plot_service.validate_tension_deviation(
            ep_num=ep_num,
            generated_tension=generated_tension,
            book_id=book_id,
            tolerance=tolerance,
        )
