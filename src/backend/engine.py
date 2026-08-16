"""
engine.py - 覇権AIエンジンコアモジュール
Gemini API との対話、プロット生成、本文執筆の全ロジックを集約。
UltimateHegemonyEngine が全機能を統合する。
"""

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING, Any, Optional, Tuple

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.backend.database import DataRepository
    from src.backend.database.core import DatabaseManager
    from src.core.llm_gateway import LLMGenerateResultProxy
    from src.backend.engine_utils import AdaptiveCooldown
    from src.services.plot_service import PlotService
    from src.agents.PlanningAgent import PlanningAgent
    from src.agents.WritingAgent import WritingAgent
    from prompts.manager import PromptManager
    from src.backend.engine_context import ContextManager
    from src.backend.sanitizer import TextFormatter
    from src.agents.audit import LogicalAuditor
    from src.backend.engine_narrative import NarrativeController
    from src.backend.engine_critique import CritiqueAgent
    from src.agents.MarketingAgent import MarketingAgent
    from src.services.bible_service import WorldBibleGenerator
    from src.agents.plot import PlotAgent
    from src.backend.engine_style_rag import StyleRagManager


# ==========================================
# UltimateHegemonyEngine（メインエンジン）
# ==========================================
class UltimateHegemonyEngine:
    """覇権小説自動生成エンジン v2.0"""

    def __init__(
        self,
        api_key: str,
        repo: Optional["DataRepository"] = None,
        db: Optional["DatabaseManager"] = None,
        llm: Optional["LLMGenerateResultProxy"] = None,
        cooldown: Optional["AdaptiveCooldown"] = None,
        plot_service: Optional["PlotService"] = None,
        # 以下を明示的に注入（後方互換のため Optional、None なら _legacy から取得）
        planner: Optional["PlanningAgent"] = None,
        writer: Optional["WritingAgent"] = None,
        pm: Optional["PromptManager"] = None,
        ctx_mgr: Optional["ContextManager"] = None,
        formatter: Optional["TextFormatter"] = None,
        validator: Optional["LogicalAuditor"] = None,
        auditor: Optional["LogicalAuditor"] = None,
        narrative: Optional["NarrativeController"] = None,
        critique: Optional["CritiqueAgent"] = None,
        marketing: Optional["MarketingAgent"] = None,
        bible_agent: Optional["WorldBibleGenerator"] = None,
        plot_agent: Optional["PlotAgent"] = None,
        style_rag: Optional["StyleRagManager"] = None,
        **legacy: Any,
    ):
        self.api_key = api_key
        self.repo = repo
        self.db = db
        self.llm = llm
        self.cooldown = cooldown
        self._legacy = legacy

        # 明示的依存を属性として保存
        self._planner = planner
        self._writer = writer
        self._pm = pm
        self._ctx_mgr = ctx_mgr
        self._formatter = formatter
        self._validator = validator
        self._auditor = auditor
        self._narrative = narrative
        self._critique = critique
        self._marketing = marketing
        self._bible_agent = bible_agent
        self._plot_agent = plot_agent
        self._style_rag = style_rag

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
        """後方互換: _legacy 辞書から依存を取得（非推奨）"""
        warnings.warn(
            f"_legacy_dep('{name}') is deprecated. Pass '{name}' explicitly to constructor.",
            DeprecationWarning,
            stacklevel=2,
        )
        if name not in self._legacy:
            raise AttributeError(
                f"'{self.__class__.__name__}' has no legacy dependency '{name}'. "
                "Inject it via constructor or upgrade the caller."
            )
        return self._legacy[name]

    # ---- 明示的依存を返すプロパティ（未設定なら _legacy_dep にフォールバック） ----

    @property
    def planner(self) -> "PlanningAgent":
        if self._planner is not None:
            return self._planner
        return self._legacy_dep("planner")

    @property
    def planning_agent(self) -> "PlanningAgent":
        return self.planner

    @property
    def writer(self) -> "WritingAgent":
        if self._writer is not None:
            return self._writer
        return self._legacy_dep("writer")

    @property
    def pm(self) -> "PromptManager":
        if self._pm is not None:
            return self._pm
        return self._legacy_dep("pm")

    @property
    def ctx_mgr(self) -> "ContextManager":
        if self._ctx_mgr is not None:
            return self._ctx_mgr
        return self._legacy_dep("ctx_mgr")

    @property
    def formatter(self) -> "TextFormatter":
        if self._formatter is not None:
            return self._formatter
        return self._legacy_dep("formatter")

    @property
    def validator(self) -> "LogicalAuditor":
        if self._validator is not None:
            return self._validator
        return self._legacy_dep("validator")

    @property
    def auditor(self) -> "LogicalAuditor":
        if self._auditor is not None:
            return self._auditor
        return self._legacy_dep("auditor")

    @property
    def narrative(self) -> "NarrativeController":
        if self._narrative is not None:
            return self._narrative
        return self._legacy_dep("narrative")

    @property
    def critique(self) -> "CritiqueAgent":
        if self._critique is not None:
            return self._critique
        return self._legacy_dep("critique")

    @property
    def marketing(self) -> "MarketingAgent":
        if self._marketing is not None:
            return self._marketing
        return self._legacy_dep("marketing")

    @property
    def bible_agent(self) -> "WorldBibleGenerator":
        if self._bible_agent is not None:
            return self._bible_agent
        return self._legacy_dep("bible_agent")

    @property
    def plot_agent(self) -> "PlotAgent":
        if self._plot_agent is not None:
            return self._plot_agent
        return self._legacy_dep("plot_agent")

    @property
    def style_rag(self) -> "StyleRagManager":
        if self._style_rag is not None:
            return self._style_rag
        return self._legacy_dep("style_rag")

    @property
    def logic_validator(self) -> "LogicalAuditor":
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
    ) -> Tuple[bool, float]:
        return await self.plot_service.validate_tension_deviation(
            ep_num=ep_num,
            generated_tension=generated_tension,
            book_id=book_id,
            tolerance=tolerance,
        )