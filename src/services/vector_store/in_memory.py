"""
src/services/vector_store/in_memory.py - Pure-Python インメモリベクトルストア
"""

from __future__ import annotations

import logging
from typing import Any

from src.services.vector_store.base import BaseVectorStore

logger = logging.getLogger(__name__)


def _metadata_matches(meta: dict[str, Any], where: dict[str, Any]) -> bool:
    for k, v in (where or {}).items():
        if meta.get(k) != v:
            return False
    return True


class InMemoryFallbackStore(BaseVectorStore):
    """Pure-Python in-memory vector store. Used when chromadb is unavailable.

    Suitable for small corpora (≤ a few thousand documents) and tests.
    Each collection maintains a FIFO ring buffer capped at ``max_items_per_collection``.
    """

    def __init__(self, max_items_per_collection: int = 10000) -> None:
        self._max = max(1, int(max_items_per_collection))
        self._data: dict[str, list[tuple[str, str, list[float], dict[str, Any]]]] = {}

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        if not na or not nb:
            return 0.0
        return dot / (na * nb)

    async def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        if not ids:
            return
        bucket = self._data.setdefault(collection_name, [])
        for i, (doc_id, doc, emb) in enumerate(zip(ids, documents, embeddings)):
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            bucket.append((doc_id, doc, list(emb), dict(meta)))
        # Trim from head (FIFO).
        if len(bucket) > self._max:
            del bucket[: len(bucket) - self._max]

    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        bucket = self._data.get(collection_name, [])
        scored: list[tuple[float, str, str, dict[str, Any]]] = []
        for doc_id, doc, emb, meta in bucket:
            if where and not _metadata_matches(meta, where):
                continue
            sim = self._cosine(query_embedding, emb)
            scored.append((sim, doc_id, doc, meta))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for sim, doc_id, doc, meta in scored[: max(0, top_k)]:
            out.append(
                {
                    "id": doc_id,
                    "content": doc,
                    "metadata": meta,
                    "distance": 1.0 - sim,
                    "similarity": sim,
                }
            )
        return out

    async def delete_by_id(self, collection_name: str, ids: list[str]) -> None:
        bucket = self._data.get(collection_name)
        if not bucket:
            return
        target = set(ids)
        self._data[collection_name] = [(i, d, e, m) for (i, d, e, m) in bucket if i not in target]

    async def clear_collection(self, collection_name: str) -> None:
        self._data.pop(collection_name, None)

    async def search_with_score(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        bucket = self._data.get(collection_name, [])
        scored: list[tuple[float, str, str, dict[str, Any]]] = []
        for doc_id, doc, emb, meta in bucket:
            if where and not _metadata_matches(meta, where):
                continue
            sim = self._cosine(query_embedding, emb)
            if sim < min_score:
                continue
            scored.append((sim, doc_id, doc, meta))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for sim, doc_id, doc, meta in scored[: max(0, top_k)]:
            out.append(
                {
                    "id": doc_id,
                    "content": doc,
                    "metadata": meta,
                    "distance": 1.0 - sim,
                    "similarity": sim,
                }
            )
        return out

    async def hybrid_search(
        self,
        collection_name: str,
        query_text: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
        alpha: float = 0.5,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Hybrid search that gracefully degrades to vector-only."""
        results = await self.search(collection_name, query_embedding, top_k=top_k, where=where)
        for r in results:
            sim = r.get("similarity", 0.0)
            r["vector_similarity"] = sim
            r["bm25_score"] = 0.0
            r["normalized_bm25"] = 0.0
            r["combined_score"] = sim
        return [r for r in results if r["combined_score"] >= min_score]


__all__ = ["InMemoryFallbackStore", "_metadata_matches"]
