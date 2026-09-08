"""Reciprocal Rank Fusion (RRF) algorithm for hybrid search (Step 19).

Fuses ranked results from multiple retrieval strategies (e.g. dense vector search
and sparse BM25 search) without requiring score scale calibration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FusionResult:
    """Represents a fused retrieval result with individual ranking and combined score."""
    doc_id: str
    score: float
    dense_rank: int | None = None
    sparse_rank: int | None = None
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def compute_rrf_scores(
    dense_rankings: list[Any],
    sparse_rankings: list[Any],
    k: int = 60,
    dense_weight: float = 1.0,
    sparse_weight: float = 1.0,
) -> list[FusionResult]:
    """Compute Reciprocal Rank Fusion (RRF) scores across dense and sparse ranking lists.

    RRF formula:
        RRF_score(d) = (w_dense / (k + rank_dense(d))) + (w_sparse / (k + rank_sparse(d)))

    Args:
        dense_rankings: List of documents/results from dense retrieval in rank order.
        sparse_rankings: List of documents/results from sparse retrieval in rank order.
        k: Smoothing constant (standard default is 60).
        dense_weight: Weight multiplier for dense ranks.
        sparse_weight: Weight multiplier for sparse ranks.

    Returns:
        List of FusionResult objects sorted by fused score descending.
    """
    def _extract_id_content_meta(item: Any) -> tuple[str, str, dict[str, Any]]:
        if isinstance(item, dict):
            return str(item.get("id", "")), str(item.get("content", "")), item.get("metadata", {})
        doc_id = getattr(item, "id", None) or getattr(item, "doc_id", "")
        content = getattr(item, "content", "")
        meta = getattr(item, "metadata", {}) or {}
        return str(doc_id), str(content), meta

    # Accumulators: doc_id -> info
    items_info: dict[str, tuple[str, dict[str, Any]]] = {}
    dense_ranks: dict[str, int] = {}
    sparse_ranks: dict[str, int] = {}

    for rank_0, item in enumerate(dense_rankings):
        doc_id, content, meta = _extract_id_content_meta(item)
        if not doc_id:
            continue
        rank = rank_0 + 1  # 1-indexed rank
        dense_ranks[doc_id] = rank
        if doc_id not in items_info:
            items_info[doc_id] = (content, meta)

    for rank_0, item in enumerate(sparse_rankings):
        doc_id, content, meta = _extract_id_content_meta(item)
        if not doc_id:
            continue
        rank = rank_0 + 1
        sparse_ranks[doc_id] = rank
        if doc_id not in items_info:
            items_info[doc_id] = (content, meta)

    # Compute fused scores for all unique doc_ids
    all_doc_ids = set(dense_ranks.keys()) | set(sparse_ranks.keys())
    results: list[FusionResult] = []

    for doc_id in all_doc_ids:
        dense_r = dense_ranks.get(doc_id)
        sparse_r = sparse_ranks.get(doc_id)

        score = 0.0
        if dense_r is not None:
            score += dense_weight / (k + dense_r)
        if sparse_r is not None:
            score += sparse_weight / (k + sparse_r)

        content, meta = items_info[doc_id]
        results.append(FusionResult(
            doc_id=doc_id,
            score=score,
            dense_rank=dense_r,
            sparse_rank=sparse_r,
            content=content,
            metadata=meta,
        ))

    # Sort descending by score
    results.sort(key=lambda x: x.score, reverse=True)
    return results
