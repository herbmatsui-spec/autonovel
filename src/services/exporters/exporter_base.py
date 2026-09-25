from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ExporterBase(ABC):
    @abstractmethod
    def export(self, episodes: List[Dict[str, Any]]) -> str:
        pass