"""Vector Store Provider Interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IVectorStoreProvider(ABC):
    """Interface for vector store providers."""

    @abstractmethod
    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None, **kwargs: Any) -> List[str]:
        """Add texts to the vector store."""
        ...

    @abstractmethod
    def query(self, query_text: str, n_results: int = 5, **kwargs: Any) -> List[Dict[str, Any]]:
        """Query similar texts from the vector store."""
        ...
