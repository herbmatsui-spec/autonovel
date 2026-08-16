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
    from prompts.manager import PromptManager
    from src.agents.audit import LogicalAuditor
    from src.agents.MarketingAgent import MarketingAgent
    from src.agents.PlanningAgent import PlanningAgent
    from src.agents.plot import PlotAgent
    from src.agents.WritingAgent import WritingAgent
    from src.backend.database import DataRepository
    from src.backend.database.core import DatabaseManager
    from src.backend.engine_context import ContextManager
    from src.backend.engine_critique import CritiqueAgent
    from src.backend.engine_narrative import NarrativeController
    from src.backend.engine_style_rag import StyleRagManager
    from src.backend.engine_utils import AdaptiveCooldown
    from src.backend.sanitizer import TextFormatter
    from src.core.llm_gateway import LLMGenerateResultProxy
    from src.services.bible_service import WorldBibleGenerator
    from src.services.plot_service import PlotService

from src.backend.engine_deps import EngineDeps


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
        deps: Optional[EngineDeps] = None,
        **legacy: Any,
    ):
        self.api_key = api_key
        self.repo = repo
        self.db = db
        self.llm = llm
        self.cooldown = cooldown
        self._legacy = legacy

        # EngineDeps から依存を設定（優先）、なければ個別引数互換は legacy 経由
        if deps is not None:
            self._planner = deps.planner
            self._writer = deps.writer
            self._pm = deps.pm
            self._ctx_mgr = deps.ctx_mgr
            self._formatter = deps.formatter
            self._validator = deps.validator
            self._auditor = deps.auditor
            self._narrative = deps.narrative
            self._critique = deps.critique
            self._marketing = deps.marketing
            self._bible_agent = deps.bible_agent
            self._plot_agent = deps.plot_agent
            self._style_rag = deps.style_rag
        else:
            # 後方互換: 明示的引数は legacy 経由で設定される想定（従来通り _legacy_dep で取得）
            self._planner = None
            self._writer = None
            self._pm = None
            self._ctx_mgr = None
            self._formatter = None
            self._validator = None
            self._auditor = None
            self._narrative = None
            self._critique = None
            self._marketing = None
            self._bible_agent = None
            self._plot_agent = None
            self._style_rag = None

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

        self.validate_dependencies()

    def validate_dependencies(self) -> None:
        """必須依存が揃っているか起動時に検証"""
        required = [
            "planner", "writer", "pm", "ctx_mgr", "formatter",
            "validator", "auditor", "narrative", "critique",
            "marketing", "bible_agent", "plot_agent", "style_rag",
        ]
        missing = [
            name for name in required
            if getattr(self, f"_{name}") is None and name not in self._legacy
        ]
        if missing:
            raise RuntimeError(
                f"Missing required dependencies: {missing}. "
                "Pass them via EngineDeps or legacy dict."
            )

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
