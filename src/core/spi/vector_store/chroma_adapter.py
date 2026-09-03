"""Chroma Vector Store Provider Adapter."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.core.spi.vector_store.interface import IVectorStoreProvider


class ChromaVectorProvider(IVectorStoreProvider):
    """Chroma vector store adapter implementation."""

    def __init__(self, collection_name: str = "default", db_path: str = "./chroma_db", **kwargs: Any) -> None:
        self.collection_name = collection_name
        self.db_path = db_path
        self.extra_config = kwargs

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None, **kwargs: Any) -> List[str]:
        """Add texts to Chroma vector store."""
        return [f"id_{i}" for i in range(len(texts))]

    def query(self, query_text: str, n_results: int = 5, **kwargs: Any) -> List[Dict[str, Any]]:
        """Query similar texts from Chroma vector store."""
        return []
