"""Cross-Encoder / Simple / Noop Reranker 実装.

``RERANKER_BACKEND`` (settings) により自動切替:
  - "none"           : NoopReranker (順序維持)
  - "simple"         : SimpleReranker (埋め込みコサイン類似度)
  - "cross_encoder"  : CrossEncoderReranker (sentence-transformers 必須)
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from src.backend.config import settings
from src.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)


class Reranker(Protocol):
    async def rerank(self, query: str, docs: list[str], top_k: int) -> list[tuple[int, float]]: ...


class NoopReranker:
    """入力をそのまま返す."""

    async def rerank(self, query: str, docs: list[str], top_k: int) -> list[tuple[int, float]]:
        n = min(max(0, top_k), len(docs))
        return [(i, 0.0) for i in range(n)]


class SimpleReranker:
    """埋め込みコサイン類似度で rerank."""

    def __init__(self, embedding_service_obj: Any | None = None) -> None:
        self._emb = embedding_service_obj or embedding_service

    @staticmethod
    def _cos(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        if not na or not nb:
            return 0.0
        return dot / (na * nb)

    async def rerank(self, query: str, docs: list[str], top_k: int) -> list[tuple[int, float]]:
        if not docs:
            return []
        qv = self._emb.get_embedding(query)
        scored: list[tuple[float, int]] = []
        for i, d in enumerate(docs):
            dv = self._emb.get_embedding(d)
            scored.append((self._cos(qv, dv), i))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [(i, s) for s, i in scored[: max(0, top_k)]]


def _has_cross_encoder() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("sentence_transformers") is not None
    except Exception:
        return False


HAS_CROSS_ENCODER = _has_cross_encoder()


class CrossEncoderReranker:
    """sentence-transformers CrossEncoder による rerank.

    ``HAS_CROSS_ENCODER=False`` のときは ``RuntimeError`` を送出.
    """

    def __init__(self, model_name: str | None = None) -> None:
        if not HAS_CROSS_ENCODER:
            raise RuntimeError(
                "CrossEncoderReranker requires sentence-transformers. "
                "Install via `pip install -e '.[rag]'`."
            )
        from sentence_transformers import CrossEncoder  # type: ignore

        self._model = CrossEncoder(model_name or settings.RERANKER_MODEL)

    async def rerank(self, query: str, docs: list[str], top_k: int) -> list[tuple[int, float]]:
        if not docs:
            return []
        pairs = [[query, d] for d in docs]
        scores = self._model.predict(pairs).tolist()
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return [(i, float(s)) for i, s in ranked[: max(0, top_k)]]


def build_default_reranker() -> Reranker:
    """``settings.RERANKER_BACKEND`` に応じた Reranker を生成する."""
    backend = (settings.RERANKER_BACKEND or "none").lower()
    if backend == "cross_encoder":
        return CrossEncoderReranker()
    if backend == "simple":
        return SimpleReranker()
    return NoopReranker()


__all__ = [
    "Reranker",
    "NoopReranker",
    "SimpleReranker",
    "CrossEncoderReranker",
    "HAS_CROSS_ENCODER",
    "build_default_reranker",
]
