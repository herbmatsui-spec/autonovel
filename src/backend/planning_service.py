"""
planning_service.py - PlanningService: 企画・プロット生成を担当するドメインサービス。

UltimateHegemonyEngine から分離したサービス。
ワークフロー (FullAutoWorkflow, PlanGenerationWorkflow 等) は PlanningService を
依存対象にし、EngineFacade 経由でインジェクトされる。

責任:
- create_hegemony_plan: 企画生成 (WorldBibleGenerator へ委譲)
- audit_bible_completeness: 整合性監査 (bible_generator.auditor へ委譲)
"""
from __future__ import annotations

from typing import Any, Optional, Tuple

from src.backend.protocols import PlanningPort
from src.shared.utils import StatusReporter


class PlanningService:
    """覇権小説の企画・プロット生成を担当するサービス。"""

    def __init__(
        self,
        bible_generator: Any,  # WorldBibleGenerator (engine.planner として注入される実体)
        repo: Any,  # DataRepository
        pm: Any,  # PromptManager
        ctx_mgr: Any,  # ContextManager
        reporter_factory: Any,  # StatusReporter 作成用 Callable
    ) -> None:
        self.bible_generator = bible_generator
        self.repo = repo
        self.pm = pm
        self.ctx_mgr = ctx_mgr
        self.reporter_factory = reporter_factory

    async def create_hegemony_plan(
        self,
        genre: str = None,
        keywords: str = None,
        style_key: str = None,
        concept: str = None,
        title: str = "",
        cheat_scale: int = 4,
        growth_curve: str = "最初からカンスト(無双)",
        system_assist: int = 70,
        cost_severity: int = 2,
        target_eps: int = 10,
        initial_plot_limit: int = 3,
        reporter: Optional[Any] = None,
    ) -> Tuple[int, Any]:
        """覇権企画を生成し、book_id と bible を返す (WorldBibleGenerator へ委譲)。"""
        return await self.bible_generator.create_hegemony_plan(
            genre=genre,
            keywords=keywords,
            style_key=style_key,
            concept=concept,
            title=title,
            cheat_scale=cheat_scale,
            growth_curve=growth_curve,
            system_assist=system_assist,
            cost_severity=cost_severity,
            target_eps=target_eps,
            initial_plot_limit=initial_plot_limit,
            reporter=reporter,
        )

    async def audit_bible_completeness(
        self,
        book_id: int,
        reporter: Any = None,
    ) -> bool:
        """Bible の整合性を監査する (bible_generator.auditor へ委譲)。"""
        auditor = getattr(self.bible_generator, "auditor", None)
        if auditor is None or not hasattr(auditor, "audit_bible_completeness"):
            return True
        return await auditor.audit_bible_completeness(book_id, reporter=reporter)
