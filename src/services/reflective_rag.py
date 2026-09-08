"""Reflective RAG Screening Service.

Phase 2 / Guideline #7: Iterative query refinement with relevance scoring
and context fit checking. LLM-free implementation using rank-bm25 and
GraphRAG consistency checks.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from src.services.rag_service import GraphRAGService, SearchResult
from src.services.vector_store import BaseVectorStore
from src.services.nlp.japanese_tokenizer import JapaneseTokenizer
from src.services.query_reformulator import QueryReformulator, QueryReformulationMode

try:
    from rank_bm25 import BM25Okapi
except Exception:
    BM25Okapi = None


@dataclass
class ContextFitResult:
    """Result of context fit check with detailed conflict information."""
    score: float  # 0.0 (forbidden) to 1.0 (fully consistent)
    is_forbidden: bool = False
    is_retired: bool = False
    status: str = "active"
    conflict_types: list[str] = field(default_factory=list)  # ["temporal", "causal", "state"]
    entity_valid: bool = True
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReflectiveDoc:
    """Single document with complete reflective metadata for citation/traceability."""
    search_result: SearchResult
    iteration_found: int
    cosine_score: float
    context_fit_score: float
    context_fit_details: ContextFitResult
    combined_score: float
    rerank_score: float | None = None
    bm25_keywords_matched: list[str] = field(default_factory=list)
    
    def to_citation_dict(self) -> dict:
        """Citation summary (JSON serializable)."""
        return {
            "id": self.search_result.id,
            "content_preview": self.search_result.content[:200] + ("..." if len(self.search_result.content) > 200 else ""),
            "source": self.search_result.source,
            "iteration": self.iteration_found,
            "scores": {
                "cosine": round(self.cosine_score, 3),
                "context_fit": round(self.context_fit_score, 3),
                "combined": round(self.combined_score, 3),
                "rerank": round(self.rerank_score, 3) if self.rerank_score is not None else None
            },
            "conflicts": self.context_fit_details.conflict_types,
            "entity_valid": self.context_fit_details.entity_valid,
            "entity_name": self.context_fit_details.details.get("entity_name"),
            "metadata": self.search_result.metadata
        }


@dataclass
class ConvergenceConfig:
    """Configuration for convergence detection in reflective retrieval."""
    min_score_improvement: float = 0.02
    score_variance_threshold: float = 0.01
    embedding_drift_threshold: float = 0.95
    min_iterations: int = 1
    max_iterations: int = 3
    rerank_top_n: int = 20
    rerank_every_n_iterations: int = 1
    enable_cross_encoder_rerank: bool = True
    lambda_neg: float = 0.5  # Contrastive BM25 negative weight


@dataclass
class ReflectiveRetrievalResult:
    documents: list[ReflectiveDoc]
    iterations: int
    converged: bool
    original_query: str
    refined_queries: list[str] = field(default_factory=list)
    initial_doc_count: int = 0
    final_doc_count: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)
    elapsed_ms: float = 0.0
    convergence_reason: str = ""
    
    def get_citations(self) -> list[dict]:
        """Get citation summaries for all documents."""
        return [d.to_citation_dict() for d in self.documents]


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
        convergence_config: ConvergenceConfig | None = None,
        tokenizer: JapaneseTokenizer | None = None,
        hybrid_retriever: Any | None = None,
        query_reformulator: QueryReformulator | None = None,
    ) -> None:
        self.rag_service = rag_service
        self.vector_store = vector_store
        self.tokenizer = tokenizer or JapaneseTokenizer()
        self.hybrid_retriever = hybrid_retriever
        self.query_reformulator = query_reformulator or QueryReformulator()
        self.top_k = top_k
        self.max_iter = max_iter
        self.relevance_threshold = relevance_threshold
        self.initial_fetch_k = initial_fetch_k
        self.timeout_seconds = timeout_seconds
        self.convergence_config = convergence_config or ConvergenceConfig(
            max_iterations=max_iter,
            min_iterations=1,
        )

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
        # Log citations for debugging/traceability
        citations_json = json.dumps(result.get_citations(), ensure_ascii=False)
        import logging
        logging.getLogger(__name__).debug(f"Reflection citations: {citations_json}")
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

    def _bm25_keyword_extract(self, 
                          pos_documents: list[SearchResult], 
                          neg_documents: list[SearchResult] | None = None,
                          n: int = 5,
                          lambda_neg: float = 0.5) -> list[str]:
        """Extract top-n discriminative keywords using BM25 over the document set.
        
        Args:
            pos_documents: Positive (filtered/passed) documents
            neg_documents: Negative (filtered out) documents for contrastive scoring
            n: Number of keywords to return
            lambda_neg: Weight for negative document scores (subtracted)
        """
        if not pos_documents:
            return []

        # BM25 available path
        if BM25Okapi is not None:
            # Positive corpus
            pos_corpus = [d.content for d in pos_documents]
            pos_tokenized = [self._tokenize(text) for text in pos_corpus]
            
            # Filter out empty tokenized docs
            pos_tokenized = [t for t in pos_tokenized if t]
            if not pos_tokenized:
                return []
            
            bm25_pos = BM25Okapi(pos_tokenized)
            
            term_scores: dict[str, float] = {}
            # Positive scores: TF weighted by effective IDF (floored to avoid 0 IDF on small corpora)
            for doc_tokens in pos_tokenized:
                tf = Counter(doc_tokens)
                for term, count in tf.items():
                    raw_idf = bm25_pos.idf.get(term, 0.0)
                    effective_idf = raw_idf if raw_idf > 0.1 else 0.5
                    term_scores[term] = term_scores.get(term, 0.0) + count * effective_idf
            
            # Negative corpus (contrastive)
            if neg_documents:
                neg_corpus = [d.content for d in neg_documents]
                neg_tokenized = [self._tokenize(text) for text in neg_corpus]
                neg_tokenized = [t for t in neg_tokenized if t]
                for doc_tokens in neg_tokenized:
                    tf = Counter(doc_tokens)
                    for term, count in tf.items():
                        if term in term_scores:
                            raw_idf = bm25_pos.idf.get(term, 0.0)
                            effective_idf = raw_idf if raw_idf > 0.1 else 0.5
                            term_scores[term] -= lambda_neg * count * effective_idf
            
            sorted_terms = sorted(term_scores.items(), key=lambda x: x[1], reverse=True)
            stop = {"の", "は", "が", "を", "に", "で", "と", "も", "や", "な", "た", "だ", "する", "ある", "いる"}
            # Only return terms with positive score (negative-filtered)
            return [t for t, s in sorted_terms if t not in stop and s > 0][:n]
        
        # Fallback: simple frequency-based (positive only)
        import re
        all_text = " ".join(d.content for d in pos_documents)
        words = [w for w in re.findall(r"[一-龯ぁ-んァ-ンa-zA-Z]{2,}", all_text)]
        if not words:
            return []
        freq = Counter(words)
        stop = {"の", "は", "が", "を", "に", "で", "と", "も", "や", "な", "た", "だ", "する", "ある", "いる"}
        return [w for w, _ in freq.most_common(n * 2) if w not in stop][:n]

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text using Japanese morphological analyzer (or fallback)."""
        if hasattr(self, "tokenizer") and self.tokenizer is not None:
            tokens = self.tokenizer.tokenize(text)
            if tokens:
                return tokens
        import re
        return [w for w in re.findall(r"[一-龯ぁ-んァ-ンa-zA-Z]{2,}", text)]

    def _compute_variance(self, values: list[float]) -> float:
        """Compute variance of a list of floats."""
        if not values:
            return 0.0
        n = len(values)
        if n == 1:
            return 0.0
        mean = sum(values) / n
        return sum((x - mean) ** 2 for x in values) / n

    def _cosine_similarity_vec(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Cosine similarity between two vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def _cosine_similarity(self, query: str, doc: SearchResult) -> float:
        """Cosine similarity between query and document (via embeddings)."""
        if hasattr(doc, 'similarity') and doc.similarity is not None:
            return float(doc.similarity)
        if hasattr(doc, 'score') and doc.score is not None:
            return float(doc.score)
        return 0.5

    def _is_semantic_drift(
        self, original_query: str, candidate_query: str, keywords: list[str]
    ) -> bool:
        """Check if candidate reformulated query drifted too far from the original intent (Step 29)."""
        orig_tokens = set(self._tokenize(original_query))
        if not orig_tokens:
            return False
        cand_tokens = set(self._tokenize(candidate_query))
        # If none of the original content words remain in the new query, it has drifted
        retained = orig_tokens & cand_tokens
        if not retained:
            return True
        return False

    def _context_fit_check(self, session: Session, doc: SearchResult, graph_name: str = "") -> ContextFitResult:
        """Check if document contradicts current World Bible (GraphRAG).

        Looks for forbidden/retired entities in the document metadata and graph.
        Returns ContextFitResult with score (0.0 forbidden to 1.0 fully consistent)
        and detailed conflict information.
        """
        meta = doc.metadata or {}
        
        # Check metadata flags first
        if meta.get("is_forbidden") or meta.get("status") in ("forbidden", "deprecated", "banned"):
            return ContextFitResult(
                score=0.0,
                is_forbidden=True,
                conflict_types=["forbidden"],
                entity_valid=False,
                details={"source": "metadata", "reason": "explicitly_forbidden"}
            )
        if meta.get("is_retired") or meta.get("status") in ("retired", "dead", "destroyed", "sealed"):
            return ContextFitResult(
                score=0.0,
                is_retired=True,
                conflict_types=["retired", "state_inactive"],
                entity_valid=False,
                details={"source": "metadata", "reason": f"entity_state_{meta.get('status', 'retired')}"}
            )

        # GraphRAG (Apache AGE) 実検証 (Step 18 & 19)
        entity_name = meta.get("entity_name") or meta.get("name")
        if not entity_name and meta.get("entities") and isinstance(meta["entities"], list):
            entity_name = meta["entities"][0] if meta["entities"] else None

        if entity_name and hasattr(self.rag_service, 'age_client') and self.rag_service.age_client:
            try:
                age_client = self.rag_service.age_client
                if hasattr(age_client, "check_entity_validity"):
                    v = age_client.check_entity_validity(session, graph_name, entity_name)
                    if isinstance(v, dict):
                        is_forbidden = bool(v.get("is_forbidden", False))
                        is_retired = bool(v.get("is_retired", False))
                        status = str(v.get("status", "active"))
                        if status in ("dead", "destroyed", "sealed", "forbidden", "retired", "deprecated"):
                            is_retired = True
                        valid = bool(v.get("valid", True)) and not is_forbidden and not is_retired
                        
                        conflict_types = []
                        if is_forbidden:
                            conflict_types.append("forbidden")
                        if is_retired:
                            conflict_types.append("retired")
                        if not valid and not is_forbidden and not is_retired:
                            conflict_types.append("invalid")
                        
                        # Determine score based on severity
                        if is_forbidden or is_retired:
                            score = 0.0
                        elif not valid:
                            score = 0.2
                        else:
                            score = 1.0
                    
                    return ContextFitResult(
                        score=score,
                        is_forbidden=is_forbidden,
                        is_retired=is_retired,
                        status=status,
                        conflict_types=conflict_types,
                        entity_valid=valid,
                        details={
                            "source": "graphrag",
                            "entity_name": entity_name,
                            "raw_result": v
                        }
                    )
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(f"Entity fit check error: {e}")
                return ContextFitResult(
                    score=0.5,
                    conflict_types=["check_failed"],
                    details={"source": "graphrag", "error": str(e)}
                )

        return ContextFitResult(score=1.0, details={"source": "default", "reason": "no_conflicts_found"})


    async def retrieve_with_reflection(
        self,
        session: Session,
        *,
        query: str,
        scene_intent: str = "",
        reformulation_mode: QueryReformulationMode = "intent_guided",
        book_id: int | None = None,
        top_k: int | None = None,
        max_iter: int | None = None,
        relevance_threshold: float | None = None,
        timeout_seconds: float | None = None,
    ) -> ReflectiveRetrievalResult:
        start_time = time.perf_counter()
        top_k = top_k or self.top_k
        max_iter = max_iter or self.convergence_config.max_iterations
        min_iter = self.convergence_config.min_iterations
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
        convergence_reason = ""
        prev_top_scores: list[float] = []
        prev_query_embedding: list[float] | None = None

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
                    convergence_reason = "timeout"
                    break

                iter_start = time.perf_counter()

                try:
                    if self.hybrid_retriever is not None:
                        candidates = self.hybrid_retriever.search(
                            query=current_query,
                            top_k=self.initial_fetch_k,
                        )
                    else:
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
                    ctx_fit_result = self._context_fit_check(session, doc)
                    ctx_fit = ctx_fit_result.score
                    combined = 0.6 * cos_sim + 0.4 * ctx_fit
                    scored.append((doc, combined, cos_sim, ctx_fit, ctx_fit_result))

                filtered = [(d, s, c, f, r) for d, s, c, f, r in scored if s >= relevance_threshold]

                # Compute convergence metrics
                top_scores = [s for _, s, _, _, _ in scored[:top_k]]
                score_variance = self._compute_variance(top_scores) if top_scores else 0.0
                
                # Score improvement check
                score_improved = False
                if prev_top_scores and top_scores:
                    avg_prev = sum(prev_top_scores) / len(prev_top_scores)
                    avg_curr = sum(top_scores) / len(top_scores)
                    if avg_curr - avg_prev >= self.convergence_config.min_score_improvement:
                        score_improved = True

                # Embedding drift check
                embedding_stable = True
                if hasattr(self.rag_service, 'embedding_service'):
                    try:
                        curr_embedding = self.rag_service.embedding_service.get_embedding(current_query)
                        if prev_query_embedding is not None:
                            drift = self._cosine_similarity_vec(prev_query_embedding, curr_embedding)
                            if drift < self.convergence_config.embedding_drift_threshold:
                                embedding_stable = False
                        prev_query_embedding = curr_embedding
                    except Exception:
                        pass

                iter_elapsed = (time.perf_counter() - iter_start) * 1000
                all_history.append({
                    "iteration": iteration + 1,
                    "query": current_query,
                    "candidates": len(candidates),
                    "filtered": len(filtered),
                    "top_scores": top_scores,
                    "score_variance": round(score_variance, 4),
                    "score_improved": score_improved,
                    "embedding_stable": embedding_stable,
                    "elapsed_ms": round(iter_elapsed, 1),
                })

                # Convergence checks
                has_enough_docs = len(filtered) >= top_k
                min_iterations_met = iteration + 1 >= min_iter
                
                if has_enough_docs and min_iterations_met:
                    # Check semantic convergence
                    stable_scores = score_variance <= self.convergence_config.score_variance_threshold
                    no_significant_improvement = not score_improved
                    embedding_converged = embedding_stable
                    
                    if stable_scores and no_significant_improvement and embedding_converged:
                        final_docs = [d for d, _, _, _, _ in filtered[:top_k]]
                        converged = True
                        convergence_reason = "semantic_convergence"
                        break
                    elif not score_improved and iteration + 1 >= min_iter:
                        # No improvement but min iterations met - converge anyway
                        final_docs = [d for d, _, _, _, _ in filtered[:top_k]]
                        converged = True
                        convergence_reason = "no_improvement"
                        break

                prev_top_scores = top_scores

                # Collect negative documents for contrastive BM25
                neg_documents = [d for d, s, c, f, r in scored if s < relevance_threshold]

                # Cross-encoder reranking for precision (Step: Priority 5)
                if (self.convergence_config.enable_cross_encoder_rerank 
                    and iteration % self.convergence_config.rerank_every_n_iterations == 0
                    and hasattr(self.rag_service, 'rerank_with_cross_encoder')
                    and len(scored) > top_k):
                    try:
                        # Prepare documents for reranking
                        rerank_candidates = scored[:self.convergence_config.rerank_top_n]
                        doc_texts = [doc.content for doc, _, _, _, _ in rerank_candidates]
                        rerank_results = await self.rag_service.rerank_with_cross_encoder(
                            current_query, doc_texts, top_k=min(top_k * 2, len(doc_texts))
                        )
                        # Apply rerank scores
                        rerank_map = {idx: score for idx, score in rerank_results}
                        new_scored = []
                        for idx, (doc, combined, cos_sim, ctx_fit, ctx_fit_result) in enumerate(rerank_candidates):
                            if idx in rerank_map:
                                # Blend original combined score with cross-encoder score
                                new_combined = 0.5 * combined + 0.5 * rerank_map[idx]
                                new_scored.append((doc, new_combined, cos_sim, ctx_fit, ctx_fit_result))
                            else:
                                new_scored.append((doc, combined, cos_sim, ctx_fit, ctx_fit_result))
                        # Add remaining scored items
                        new_scored.extend(scored[self.convergence_config.rerank_top_n:])
                        scored = new_scored
                        # Re-filter after reranking
                        filtered = [(d, s, c, f, r) for d, s, c, f, r in scored if s >= relevance_threshold]
                        # Update negative documents after reranking
                        neg_documents = [d for d, s, c, f, r in scored if s < relevance_threshold]
                        all_history[-1]["reranked"] = True
                        all_history[-1]["rerank_count"] = len(rerank_results)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).debug(f"Cross-encoder rerank failed: {e}")
                        all_history[-1]["reranked"] = False
                        all_history[-1]["rerank_error"] = str(e)

                pos_docs = [d for d, _, _, _, _ in filtered] if filtered else [d for d, _, _, _, _ in scored[:top_k]]
                pos_ids = {d.id for d in pos_docs}
                contrastive_neg = [d for d in neg_documents if d.id not in pos_ids] if neg_documents else None
                keywords = self._bm25_keyword_extract(
                    pos_docs, 
                    neg_documents=contrastive_neg,
                    n=5,
                    lambda_neg=self.convergence_config.lambda_neg
                )

                if keywords:
                    candidate_query = self.query_reformulator.reformulate_query(
                        query=current_query,
                        keywords=keywords,
                        scene_intent=scene_intent,
                        mode=reformulation_mode,
                    )
                    if self._is_semantic_drift(query, candidate_query, keywords):
                        final_docs = [d for d, _, _, _, _ in filtered[:top_k]] if filtered else [d for d, _, _, _, _ in scored[:top_k]]
                        converged = True
                        convergence_reason = "drift_prevented"
                        break
                    current_query = candidate_query
                    refined_queries.append(current_query)
                else:
                    final_docs = [d for d, _, _, _, _ in scored[:top_k]]
                    converged = False
                    convergence_reason = "no_keywords"
                    break
            else:
                final_docs = [d for d, _, _, _, _ in scored[:top_k]]
                converged = False
                convergence_reason = "max_iterations_reached"

        except Exception as e:
            # 予期せぬ例外時の安全フォールバック (Step 23)
            import logging
            logging.getLogger(__name__).warning(f"Unexpected error in retrieve_with_reflection: {e}")
            final_docs = initial_candidates[:top_k] if initial_candidates else []
            converged = False
            convergence_reason = "error"

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Build ReflectiveDoc objects with full metadata
        reflective_docs = []
        for doc in final_docs:
            # Find matching scored entry for this document
            scored_entry = next(
                ((d, comb, cos, ctx, ctx_res) for d, comb, cos, ctx, ctx_res in scored if d.id == doc.id), 
                None
            )
            if scored_entry:
                _, combined, cos_sim, ctx_fit, ctx_fit_result = scored_entry
                # Check for rerank score in history
                rerank_score = None
                if all_history and "reranked" in all_history[-1] and all_history[-1].get("reranked"):
                    # Approximate: use the blended score if reranking happened
                    pass
                # Find BM25 keywords matched in this doc
                matched_kws = []
                if refined_queries and len(refined_queries) > 1:
                    last_query = refined_queries[-1]
                    matched_kws = [kw for kw in last_query.split() if kw in doc.content]
            else:
                combined = cos_sim = ctx_fit = 0.0
                ctx_fit_result = ContextFitResult(score=1.0)
                rerank_score = None
                matched_kws = []
            
            reflective_docs.append(ReflectiveDoc(
                search_result=doc,
                iteration_found=iteration + 1,
                cosine_score=cos_sim,
                context_fit_score=ctx_fit,
                context_fit_details=ctx_fit_result,
                combined_score=combined,
                rerank_score=rerank_score,
                bm25_keywords_matched=matched_kws
            ))

        result = ReflectiveRetrievalResult(
            documents=reflective_docs,
            iterations=iteration + 1,
            converged=converged,
            original_query=query,
            refined_queries=refined_queries,
            initial_doc_count=initial_count,
            final_doc_count=len(final_docs),
            history=all_history,
            elapsed_ms=elapsed_ms,
            convergence_reason=convergence_reason,
        )

        # 反射反復ログのDB永続化連携 (Step 22)
        if session is not None:
            self.save_reflection_history(session, result, book_id=book_id)

        return result

    async def retrieve_reflective_async(
        self,
        session: Session,
        *,
        query: str,
        scene_intent: str = "",
        reformulation_mode: QueryReformulationMode = "intent_guided",
        book_id: int | None = None,
        top_k: int | None = None,
        max_iter: int | None = None,
        relevance_threshold: float | None = None,
        timeout_seconds: float | None = None,
    ) -> ReflectiveRetrievalResult:
        """Asynchronous API entry point for reflective retrieval (Step 34)."""
        return await self.retrieve_with_reflection(
            session=session,
            query=query,
            scene_intent=scene_intent,
            reformulation_mode=reformulation_mode,
            book_id=book_id,
            top_k=top_k,
            max_iter=max_iter,
            relevance_threshold=relevance_threshold,
            timeout_seconds=timeout_seconds,
        )

    def format_for_prompt(
        self, result: ReflectiveRetrievalResult, max_chars: int = 3000
    ) -> str:
        """Format reflective retrieval results into a clean context prompt block (Step 35)."""
        if not result.documents:
            return "【参照世界観設定】：該当する設定記述はありませんでした。"

        lines = ["【参照世界観設定（反射的整合性検証済）】:"]
        curr_chars = len(lines[0])
        for idx, r_doc in enumerate(result.documents, 1):
            doc = r_doc.search_result
            title = doc.metadata.get("title") or doc.metadata.get("name") or f"資料{idx}"
            source = doc.source or "world_bible"
            score_str = f"適合度: {r_doc.combined_score:.2f}"
            entry = f"\n- [{title}] ({source} / {score_str})\n  {doc.content.strip()}\n"

            if curr_chars + len(entry) > max_chars:
                break
            lines.append(entry)
            curr_chars += len(entry)

        return "\n".join(lines)


__all__ = ["ReflectiveRAGService", "ReflectiveRetrievalResult", "ConvergenceConfig", "ContextFitResult", "ReflectiveDoc"]