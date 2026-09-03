"""Mock Vector Store Provider Adapter."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.spi.vector_store.interface import IVectorStoreProvider


class MockVectorProvider(IVectorStoreProvider):
    """Mock vector store provider for tests."""

    def __init__(self, **kwargs: Any) -> None:
        self.config = kwargs
        self._storage: List[Dict[str, Any]] = []

    def add_texts(
        self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None, **kwargs: Any
    ) -> List[str]:
        ids = []
        for i, text in enumerate(texts):
            doc_id = f"mock_{len(self._storage)}"
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            self._storage.append({"id": doc_id, "text": text, "metadata": meta})
            ids.append(doc_id)
        return ids

    def query(self, query_text: str, n_results: int = 5, **kwargs: Any) -> List[Dict[str, Any]]:
        return self._storage[:n_results]
