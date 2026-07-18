from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.backend.engine import UltimateHegemonyEngine
from src.backend.protocols import WritingPort, CritiquePort, BiblePort, TensionPort
from src.shared.utils import StatusReporter
from src.backend.planning_service import PlanningService
from src.backend.writing_service import WritingService
from src.backend.database import DataRepository


class BaseWorkflow(ABC):
    """
    Abstract base class for all domain workflows.
    Each workflow encapsulates a single use case of the application.

    Phase 4 (ADR-0004) より、engine に加えてドメインサービス
    (WritingService, PlanningService 等) を受け取れるよう拡張した。
    engine は任意（後方互換のため Optional）とし、services は
    注入されなければ engine から委譲する。
    """
    def __init__(
        self,
        engine: Optional[UltimateHegemonyEngine] = None,
        writing: Optional[WritingPort] = None,
        planner: Optional[PlanningService] = None,
        writing_service: Optional[WritingService] = None,
        repo: Optional[DataRepository] = None,
        critique: Optional[CritiquePort] = None,
        narrative: Optional[Any] = None,
        marketing: Optional[Any] = None,
        bible_agent: Optional[BiblePort] = None,
        plot_agent: Optional[Any] = None,
        formatter: Optional[Any] = None,
        vector_store: Optional[Any] = None,
        llm_client: Optional[Any] = None,
        tension: Optional[TensionPort] = None,
    ):
        self.engine = engine
        # WritingPort: 注入されなければ engine.writer で代用（後方互換）
        self.writing: WritingPort = writing if writing is not None else (getattr(engine, "writer", None) if engine else None)
        # PlanningService: 注入されなければ engine.planner で代用
        self.planner: Optional[PlanningService] = planner if planner is not None else (getattr(engine, "planner", None) if engine else None)
        # WritingService: 注入されなければ engine.writer で代用（プロトコル互換）
        self.writing_service: Optional[WritingService] = writing_service if writing_service is not None else (getattr(engine, "writer", None) if engine else None)
        # DataRepository: 注入されなければ engine.repo で代用
        self.repo: Optional[DataRepository] = repo if repo is not None else (getattr(engine, "repo", None) if engine else None)
        # その他のサービスポート
        self.critique: Optional[CritiquePort] = critique if critique is not None else (getattr(engine, "critique", None) if engine else None)
        self.narrative: Optional[Any] = narrative if narrative is not None else (getattr(engine, "narrative", None) if engine else None)
        self.marketing: Optional[Any] = marketing if marketing is not None else (getattr(engine, "marketing", None) if engine else None)
        self.bible_agent: Optional[BiblePort] = bible_agent if bible_agent is not None else (getattr(engine, "bible_agent", None) if engine else None)
        self.plot_agent: Optional[Any] = plot_agent if plot_agent is not None else (getattr(engine, "plot_agent", None) if engine else None)
        self.formatter: Optional[Any] = formatter if formatter is not None else (getattr(engine, "formatter", None) if engine else None)
        # Prefetch 用
        self.vector_store: Optional[Any] = vector_store if vector_store is not None else getattr(engine, "vector_store", None)
        self.llm_client: Optional[Any] = llm_client if llm_client is not None else (getattr(engine, "llm_client", None) or getattr(engine, "client", None))
        # TensionService: 注入されなければ engine の tension_agent で代用、
        # なければ engine のメソッドで代用（engine が TensionPort 相当のメソッドを持つため）
        self.tension: Optional[TensionPort] = tension if tension is not None else (
            getattr(engine, "tension_agent", None) if engine else None
        )
        if self.tension is None and engine is not None:
            # engine が直接 determine_target_tension / validate_tension_deviation を持つ場合は
            # engine 自身を tension として利用（後方互換）
            if hasattr(engine, "determine_target_tension") and hasattr(engine, "validate_tension_deviation"):
                self.tension = engine

    @abstractmethod
    async def execute(self, reporter: StatusReporter, **kwargs) -> Dict[str, Any]:
        """
        Execute the workflow logic.
        """
        pass
