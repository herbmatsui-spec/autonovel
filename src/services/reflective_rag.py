"""Reflective RAG Screening Service.

Phase 2 / Guideline #7: Iterative query refinement with relevance scoring
and context fit checking. LLM-free implementation using rank-bm25 and
GraphRAG consistency checks.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from src.services.rag_service import GraphRAGService, SearchResult
from src.services.vector_store import BaseVectorStore

try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None


@dataclass
class ReflectiveRetrievalResult:
    documents: list[SearchResult]
    iterations: int
    converged: bool
    original_query: str
    refined_queries: list[str] = field(default_factory=list)
    initial_doc_count: int = 0
    final_doc_count: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: float = 0.0


class ReflectiveRAGService:
    """Iterative RAG retrieval with query refinement.

    Process (max T iterations):
    1. Initial vector search (Top-K)
    2. Score each doc: 0.6 * cosine + 0.4 * context_fit
    3. Filter below threshold
    4. If enough docs -> converged
    5. Extract keywords from remaining (BM25)
    6. Refine query: original + keywords (AND)
    7. Repeat
    """

    def __init__(
        self,
        rag_service: GraphRAGService,
        vector_store: BaseVectorStore | None = None,
        top_k: int = 5,
        max_iter: int = 3,
        relevance_threshold: float = 0.5,
        initial_fetch_k: int = 10,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.rag_service = rag_service
        self.vector_store = vector_store
        self.top_k = top_k
        self.max_iter = max_iter
        self.relevance_threshold = relevance_threshold
        self.initial_fetch_k = initial_fetch_k
        self.timeout_seconds = timeout_seconds

    def save_reflection_history(
        self,
        session: Session,
        result: ReflectiveRetrievalResult,
        *,
        book_id: int | None = None,
        session_id: str | None = None,
    ) -> None:
        """Persist reflective retrieval metrics into rag_reflection_history table (Step 22)."""
        if not session or not hasattr(session, "execute"):
            return

        import json
        import uuid
        from datetime import datetime, timezone
        from sqlalchemy import text

        sess_id = session_id or str(uuid.uuid4())
        refined_json = json.dumps(result.refined_queries, ensure_ascii=False)
        now = datetime.now(timezone.utc)

        stmt = text("""
            INSERT INTO rag_reflection_history (
                session_id, book_id, original_query, refined_queries_json,
                iterations, initial_doc_count, final_doc_count, converged, created_at
            ) VALUES (
                :session_id, :book_id, :original_query, :refined_queries_json,
                :iterations, :initial_doc_count, :final_doc_count, :converged, :created_at
            )
        """)
        try:
            session.execute(
                stmt,
                {
                    "session_id": sess_id,
                    "book_id": book_id,
                    "original_query": result.original_query,
                    "refined_queries_json": refined_json,
                    "iterations": result.iterations,
                    "initial_doc_count": result.initial_doc_count,
                    "final_doc_count": result.final_doc_count,
                    "converged": result.converged,
                    "created_at": now,
                },
            )
            if hasattr(session, "flush"):
                session.flush()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to persist rag_reflection_history: {e}")

    def _bm25_keyword_extract(self, documents: list[SearchResult], n: int = 5) -> list[str]:
        """Extract top-n discriminative keywords using BM25 over the document set."""
        if not documents or BM25Okapi is None:
            # Fallback: simple frequency-based
            from collections import Counter
            import re
            all_text = " ".join(d.content for d in documents)
            words = [w for w in re.findall(r"[一-龯ぁ-んァ-ンa-zA-Z]{2,}", all_text)]
            if not words:
                return []
            freq = Counter(words)
            stop = {"の", "は", "が", "を", "に", "で", "と", "も", "や", "な", "た", "だ", "する", "ある", "いる"}
            return [w for w, _ in freq.most_common(n * 2) if w not in stop][:n]

        corpus = [d.content for d in documents]
        tokenized = [self._tokenize(text) for text in corpus]
        bm25 = BM25Okapi(tokenized)

        term_scores: dict[str, float] = {}
        for doc_tokens in tokenized:
            if not doc_tokens:
                continue
            scores = bm25.get_scores(doc_tokens)
            for term, score in zip(doc_tokens, scores):
                term_scores[term] = term_scores.get(term, 0.0) + score

        sorted_terms = sorted(term_scores.items(), key=lambda x: x[1], reverse=True)
        stop = {"の", "は", "が", "を", "に", "で", "と", "も", "や", "な", "た", "だ", "する", "ある", "いる"}
        return [t for t, _ in sorted_terms if t not in stop][:n]

    def _tokenize(self, text: str) -> list[str]:
        import re
        return [w for w in re.findall(r"[一-龯ぁ-んァ-ンa-zA-Z]{2,}", text)]

    def _cosine_similarity(self, query: str, doc: SearchResult) -> float:
        """Cosine similarity between query and document (via embeddings)."""
        if hasattr(doc, 'similarity') and doc.similarity is not None:
            return float(doc.similarity)
        if hasattr(doc, 'score') and doc.score is not None:
            return float(doc.score)
        return 0.5

    def _context_fit_check(self, session: Session, doc: SearchResult, graph_name: str = "") -> float:
        """Check if document contradicts current World Bible (GraphRAG).

        Looks for forbidden/retired entities in the document metadata and graph.
        Returns 0.0 (forbidden) to 1.0 (fully consistent).
        """
        meta = doc.metadata or {}
        if meta.get("is_forbidden") or meta.get("is_retired"):
            return 0.0

        # GraphRAG (Apache AGE) 実検証 (Step 18 & 19)
        entity_name = meta.get("entity_name") or meta.get("name")
        if not entity_name and meta.get("entities") and isinstance(meta["entities"], list):
            entity_name = meta["entities"][0] if meta["entities"] else None

        if entity_name and hasattr(self.rag_service, 'age_client') and self.rag_service.age_client:
            try:
                age_client = self.rag_service.age_client
                if hasattr(age_client, "check_entity_validity"):
                    v = age_client.check_entity_validity(session, graph_name, entity_name)
                    if v.get("is_forbidden") or v.get("is_retired"):
                        return 0.0
                    if not v.get("valid", True):
                        return 0.2
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(f"Entity fit check error: {e}")

        return 1.0


    async def retrieve_with_reflection(
        self,
        session: Session,
        *,
        query: str,
        book_id: int | None = None,
        top_k: int | None = None,
        max_iter: int | None = None,
        relevance_threshold: float | None = None,
        timeout_seconds: float | None = None,
    ) -> ReflectiveRetrievalResult:
        start_time = time.perf_counter()
        top_k = top_k or self.top_k
        max_iter = max_iter or self.max_iter
        relevance_threshold = relevance_threshold or self.relevance_threshold
        effective_timeout = (
            timeout_seconds if timeout_seconds is not None else self.timeout_seconds
        )

        current_query = query
        refined_queries = [query]
        all_history = []
        initial_candidates = []
        initial_count = 0
        scored = []
        filtered = []
        final_docs = []
        converged = False
        iteration = 0

        try:
            for iteration in range(max_iter):
                # タイムアウト検知 (Step 23)
                if (time.perf_counter() - start_time) >= effective_timeout:
                    import logging
                    logging.getLogger(__name__).warning(
                        f"Reflective RAG timeout ({effective_timeout}s) reached at iteration {iteration + 1}"
                    )
                    if filtered:
                        final_docs = [d for d, _, _, _ in filtered[:top_k]]
                    elif scored:
                        final_docs = [d for d, _, _, _ in scored[:top_k]]
                    elif initial_candidates:
                        final_docs = initial_candidates[:top_k]
                    converged = False
                    break

                iter_start = time.perf_counter()

                try:
                    candidates = self.rag_service.search_similar_chunks(
                        session,
                        query=current_query,
                        limit=self.initial_fetch_k,
                        min_score=0.0,
                    )
                except Exception as search_err:
                    import logging
                    logging.getLogger(__name__).warning(f"search_similar_chunks error: {search_err}")
                    candidates = initial_candidates

                if iteration == 0:
                    initial_candidates = list(candidates)
                    initial_count = len(candidates)

                scored = []
                for doc in candidates:
                    cos_sim = self._cosine_similarity(current_query, doc)
                    ctx_fit = self._context_fit_check(session, doc)
                    combined = 0.6 * cos_sim + 0.4 * ctx_fit
                    scored.append((doc, combined, cos_sim, ctx_fit))

                filtered = [(d, s, c, f) for d, s, c, f in scored if s >= relevance_threshold]

                iter_elapsed = (time.perf_counter() - iter_start) * 1000
                all_history.append({
                    "iteration": iteration + 1,
                    "query": current_query,
                    "candidates": len(candidates),
                    "filtered": len(filtered),
                    "elapsed_ms": round(iter_elapsed, 1),
                })

                if len(filtered) >= top_k:
                    final_docs = [d for d, _, _, _ in filtered[:top_k]]
                    converged = True
                    break

                if filtered:
                    keywords = self._bm25_keyword_extract([d for d, _, _, _ in filtered], n=5)
                else:
                    keywords = self._bm25_keyword_extract([d for d, _, _, _ in scored[:top_k]], n=5)

                if keywords:
                    current_query = f"{current_query} {' '.join(keywords)}"
                    refined_queries.append(current_query)
                else:
                    final_docs = [d for d, _, _, _ in scored[:top_k]]
                    converged = False
                    break
            else:
                final_docs = [d for d, _, _, _ in scored[:top_k]]
                converged = False

        except Exception as e:
            # 予期せぬ例外時の安全フォールバック (Step 23)
            import logging
            logging.getLogger(__name__).warning(f"Unexpected error in retrieve_with_reflection: {e}")
            final_docs = initial_candidates[:top_k] if initial_candidates else []
            converged = False

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        result = ReflectiveRetrievalResult(
            documents=final_docs,
            iterations=iteration + 1,
            converged=converged,
            original_query=query,
            refined_queries=refined_queries,
            initial_doc_count=initial_count,
            final_doc_count=len(final_docs),
            history=all_history,
            elapsed_ms=elapsed_ms,
        )

        # 反射反復ログのDB永続化連携 (Step 22)
        if session is not None:
            self.save_reflection_history(session, result, book_id=book_id)

        return result


__all__ = ["ReflectiveRAGService", "ReflectiveRetrievalResult"]