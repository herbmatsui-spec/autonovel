from abc import ABC, abstractmethod
from typing import Any, Dict

from src.backend.engine import UltimateHegemonyEngine
from src.shared.utils import StatusReporter


class BaseWorkflow(ABC):
    """
    Abstract base class for all domain workflows.
    Each workflow encapsulates a single use case of the application.
    """
    def __init__(self, engine: UltimateHegemonyEngine):
        self.engine = engine

    @abstractmethod
    async def execute(self, reporter: StatusReporter, **kwargs) -> Dict[str, Any]:
        """
        Execute the workflow logic.
        """
        pass
