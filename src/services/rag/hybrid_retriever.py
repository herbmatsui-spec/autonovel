"""Hybrid Retriever combining Dense and Sparse Search with RRF (Steps 21 & 23).

Fuses dense vector semantic retrieval with sparse BM25 keyword retrieval using
Reciprocal Rank Fusion, deduplicating identical passages and normalizing scores.
"""

from __future__ import annotations

import logging
from typing import Any

from src.services.rag_service import SearchResult
from src.services.rrf_fusion import FusionResult, compute_rrf_scores
from src.services.sparse_retriever import BM25SparseRetriever

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Combines dense vector retrieval and sparse BM25 retrieval via RRF."""

    def __init__(
        self,
        dense_retriever: Any,
        sparse_retriever: BM25SparseRetriever,
        default_rrf_k: int = 60,
        dense_weight: float = 1.0,
        sparse_weight: float = 1.0,
    ) -> None:
        self.dense_retriever = dense_retriever
        self.sparse_retriever = sparse_retriever
        self.default_rrf_k = default_rrf_k
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight

    async def search_async(
        self,
        query: str,
        top_k: int = 5,
        fetch_k: int = 20,
    ) -> list[SearchResult]:
        """Asynchronously execute dense and sparse searches and fuse with RRF."""
        # 1. Fetch dense results
        dense_results: list[SearchResult] = []
        if hasattr(self.dense_retriever, "search_async"):
            dense_results = await self.dense_retriever.search_async(query, top_k=fetch_k)
        elif hasattr(self.dense_retriever, "search"):
            dense_results = self.dense_retriever.search(query, top_k=fetch_k)

        # 2. Fetch sparse results (CPU-bound)
        sparse_results = self.sparse_retriever.search(query, top_k=fetch_k)

        return self.fuse_results(dense_results, sparse_results, top_k=top_k)

    def search(
        self,
        query: str,
        top_k: int = 5,
        fetch_k: int = 20,
    ) -> list[SearchResult]:
        """Synchronously execute dense and sparse searches and fuse with RRF."""
        dense_results: list[SearchResult] = []
        if hasattr(self.dense_retriever, "search"):
            dense_results = self.dense_retriever.search(query, top_k=fetch_k)

        sparse_results = self.sparse_retriever.search(query, top_k=fetch_k)
        return self.fuse_results(dense_results, sparse_results, top_k=top_k)

    def fuse_results(
        self,
        dense_results: list[SearchResult],
        sparse_results: list[SearchResult],
        top_k: int = 5,
    ) -> list[SearchResult]:
        """Fuse and deduplicate dense and sparse results using RRF with score normalization (Step 23)."""
        fused: list[FusionResult] = compute_rrf_scores(
            dense_rankings=dense_results,
            sparse_rankings=sparse_results,
            k=self.default_rrf_k,
            dense_weight=self.dense_weight,
            sparse_weight=self.sparse_weight,
        )

        if not fused:
            return []

        # Normalize RRF scores to [0.0, 1.0] for downstream threshold consistency
        max_score = fused[0].score if fused else 1.0
        if max_score <= 0.0:
            max_score = 1.0

        top_fused = fused[:top_k]
        final_results: list[SearchResult] = []

        for item in top_fused:
            norm_score = item.score / max_score
            meta = dict(item.metadata)
            meta["rrf_raw_score"] = item.score
            meta["dense_rank"] = item.dense_rank
            meta["sparse_rank"] = item.sparse_rank

            final_results.append(SearchResult(
                id=item.doc_id,
                content=item.content,
                metadata=meta,
                source="hybrid_rrf",
                score=norm_score,
                similarity=norm_score,
            ))

        return final_results
