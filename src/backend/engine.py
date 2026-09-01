"""
engine.py - 覇権AIエンジンコアモジュール
Gemini API との対話、プロット生成、本文執筆の全ロジックを集約。
UltimateHegemonyEngine が全機能を統合する。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ==========================================
# UltimateHegemonyEngine（メインエンジン）
# ==========================================
class UltimateHegemonyEngine:
    """覇権小説自動生成エンジン v2.0"""

    def __init__(
        self,
        api_key: str,
        repo=None,
        db=None,
        llm=None,
        cooldown=None,
        plot_service=None,
        **legacy,
    ):
        self.api_key = api_key
        self.repo = repo
        self.db = db
        self.llm = llm
        self.cooldown = cooldown
        self._legacy = legacy
        self.client = None
        self.current_ep_num = 0

        if plot_service is not None:
            self.plot_service = plot_service
        elif repo is not None:
            from src.services.plot_service import PlotService

            # PlotService is repo-only by design; llm is held by the engine itself.
            self.plot_service = PlotService(repo=repo)
        else:
            self.plot_service = None

    def _legacy_dep(self, name: str) -> Any:
        if name not in self._legacy:
            raise AttributeError(
                f"'{self.__class__.__name__}' has no lazy dependency '{name}'. "
                "Inject it via constructor or upgrade the caller."
            )
        return self._legacy[name]

    @property
    def planner(self):
        return self._legacy_dep("planner")

    @property
    def planning_agent(self):
        return self._legacy_dep("planner")

    @property
    def writer(self):
        return self._legacy_dep("writer")

    @property
    def pm(self):
        return self._legacy_dep("pm")

    @property
    def ctx_mgr(self):
        return self._legacy_dep("ctx_mgr")

    @property
    def formatter(self):
        return self._legacy_dep("formatter")

    @property
    def validator(self):
        return self._legacy_dep("validator")

    @property
    def auditor(self):
        return self._legacy_dep("auditor")

    @property
    def narrative(self):
        return self._legacy_dep("narrative")

    @property
    def critique(self):
        return self._legacy_dep("critique")

    @property
    def marketing(self):
        return self._legacy_dep("marketing")

    @property
    def bible_agent(self):
        return self._legacy_dep("bible_agent")

    @property
    def plot_agent(self):
        return self._legacy_dep("plot_agent")

    @property
    def style_rag(self):
        return self._legacy_dep("style_rag")

    @property
    def ai_api(self):
        import warnings

        warnings.warn(
            "ai_api is deprecated, use llm instead",
            FutureWarning,
            stacklevel=2,
        )
        return self.llm

    @property
    def llm_client(self):
        import warnings

        warnings.warn(
            "llm_client is deprecated, use llm instead",
            FutureWarning,
            stacklevel=2,
        )
        return self.llm

    @property
    def logic_validator(self):
        return self.validator

    @property
    def generate_json(self):
        return self.llm.generate_json

    def dispose(self) -> None:
        if hasattr(self.db, "engine"):
            self.db.engine.dispose()

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
        self, book_id: int, ep_num: int, genre: str, story_type: str | None = None
    ) -> float:
        return await self.plot_service.determine_target_tension(
            book_id=book_id, ep_num=ep_num, genre=genre, story_type=story_type
        )

    async def validate_tension_deviation(
        self, ep_num: int, generated_tension: float, book_id: int, tolerance: float = 0.2
    ) -> tuple[bool, float]:
        return await self.plot_service.validate_tension_deviation(
            ep_num=ep_num,
            generated_tension=generated_tension,
            book_id=book_id,
            tolerance=tolerance,
        )
