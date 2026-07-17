from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.backend.engine import UltimateHegemonyEngine
from src.backend.protocols import WritingPort, CritiquePort, BiblePort
from src.shared.utils import StatusReporter


class BaseWorkflow(ABC):
    """
    Abstract base class for all domain workflows.
    Each workflow encapsulates a single use case of the application.

    Phase 4 (ADR-0004) より、engine に加えてドメインサービス
    (WritingService 等) を受け取れるよう拡張した。後方互換のため
    engine は必須のままとし、services は任意（engine から委譲）とする。
    """
    def __init__(
        self,
        engine: UltimateHegemonyEngine,
        writing: Optional[WritingPort] = None,
    ):
        self.engine = engine
        # WritingService が注入されなければ engine.writer で代用（後方互換）
        self.writing: WritingPort = writing if writing is not None else engine.writer

    @abstractmethod
    async def execute(self, reporter: StatusReporter, **kwargs) -> Dict[str, Any]:
        """
        Execute the workflow logic.
        """
        pass
