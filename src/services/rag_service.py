"""GraphRAG 検索・コンテキスト構築サービスモジュール (ハイブリッド検索・Reranking 対応).

Enhanced with:
- Hybrid search: Vector + Graph + Full-text (tsvector) fusion
- Reciprocal Rank Fusion (RRF) for result merging
- Cross-Encoder reranking support
- Async operations
- Token budget management
- Redis/local caching
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.backend.config import settings
from src.backend.logging_config import get_logger
from src.infrastructure.database.models.chunk import HAS_PGVECTOR, ChapterChunk
from src.services.age_client import age_client
from src.services.embedding_service import embedding_service
from src.services.vector_store import BaseVectorStore, get_default_store

if TYPE_CHECKING:
    from src.services.reranker import Reranker

logger = get_logger("rag_service")


@dataclass
class SearchResult:
    """統合検索結果."""
    id: str
    content: str
    metadata: dict[str, Any]
    source: str  # "vector", "graph", "fulltext"
    score: float
    distance: float | None = None
    similarity: float | None = None


@dataclass
class RagContext:
    """RAGコンテキスト構築結果."""
    graph_context: str
    vector_context: str
    fulltext_context: str
    stats: dict[str, Any]
    token_estimate: int


class GraphRAGService:
    """ベクトル検索・グラフ探索・全文検索を統合したハイブリッドRAGサービス."""

    def __init__(
        self,
        reranker: Reranker | None = None,
        vector_store: BaseVectorStore | None = None,
        *,
        token_budget: int = 3000,
        enable_cache: bool = True,
    ) -> None:
        self._reranker = reranker
        self._vector_store = vector_store or get_default_store()
        self._last_call_stats: dict[str, Any] = {}
        self._token_budget = token_budget
        self._enable_cache = enable_cache
        self._cache: dict[str, tuple[RagContext, float]] = {}  # key -> (context, timestamp)
        self._cache_ttl = 300  # 5分

    def get_reranker(self) -> Reranker:
        """遅延初期化で Reranker を返す."""
        if self._reranker is None:
            from src.services.reranker import build_default_reranker

            self._reranker = build_default_reranker()
        return self._reranker

    def get_last_stats(self) -> dict[str, Any]:
        return dict(self._last_call_stats)

    def _get_cache_key(self, *args: str) -> str:
        """キャッシュキー生成."""
        import hashlib
        return hashlib.md5("|".join(args).encode()).hexdigest()

    def _get_cached(self, key: str) -> RagContext | None:
        """キャッシュから取得（TTLチェック付き）."""
        if not self._enable_cache:
            return None
        if key in self._cache:
            context, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return context
            else:
                del self._cache[key]
        return None

    def _set_cache(self, key: str, context: RagContext) -> None:
        """キャッシュに保存."""
        if self._enable_cache:
            self._cache[key] = (context, time.time())

    def search_similar_chunks(
        self,
        session: Session,
        query: str,
        limit: int = 5,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        """ベクトル類似度検索（pgvector優先、SQLiteフォールバック）."""
        if not query or not query.strip():
            return []

        start = time.perf_counter()
        try:
            # PostgreSQL + pgvector 環境
            if HAS_PGVECTOR and settings.DATABASE_URL.startswith("postgresql"):
                query_vector = embedding_service.get_embedding(query)
                stmt = text(
                    """
                    SELECT id, content, chunk_metadata, embedding <=> :query_vector AS distance
                    FROM chapter_chunks
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> :query_vector
                    LIMIT :limit
                    """
                )
                result = session.execute(
                    stmt, {"query_vector": str(query_vector), "limit": limit * 2}
                )
                rows = []
                for row in result:
                    distance = float(row.distance) if row.distance is not None else 1.0
                    similarity = 1.0 - distance
                    if similarity >= min_score:
                        rows.append(SearchResult(
                            id=str(row.id),
                            content=row.content,
                            metadata=row.chunk_metadata or {},
                            source="vector",
                            score=similarity,
                            distance=distance,
                            similarity=similarity,
                        ))

                self._last_call_stats = {
                    "backend": "pgvector",
                    "hits": len(rows),
                    "limit": limit,
                    "elapsed_ms": int((time.perf_counter() - start) * 1000),
                }
                return rows[:limit]

            elif settings.REQUIRE_PG:
                raise RuntimeError(
                    "REQUIRE_PG is True but pgvector is unavailable or DATABASE_URL "
                    "is not PostgreSQL. Install pgvector or set REQUIRE_PG=false."
                )
            else:
                # SQLite フォールバック
                chunks = (
                    session.query(ChapterChunk)
                    .order_by(ChapterChunk.created_at.desc())
                    .limit(limit * 3)
                    .all()
                )
                if not chunks:
                    self._last_call_stats = {
                        "backend": "sqlite_fallback",
                        "hits": 0,
                        "limit": limit,
                        "elapsed_ms": int((time.perf_counter() - start) * 1000),
                    }
                    return []

                query_emb = embedding_service.get_embedding(query)
                scored: list[SearchResult] = []
                for c in chunks:
                    chunk_text = str(c.content) if c.content is not None else ""
                    if not chunk_text:
                        continue
                    c_emb = embedding_service.get_embedding(chunk_text)
                    sim = self._cosine_similarity(query_emb, c_emb)
                    if sim >= min_score:
                        scored.append(SearchResult(
                            id=str(c.id),
                            content=chunk_text,
                            metadata=dict(c.chunk_metadata) if c.chunk_metadata else {},
                            source="vector",
                            score=sim,
                            distance=1.0 - sim,
                            similarity=sim,
                        ))

                scored.sort(key=lambda x: x.score, reverse=True)
                rows = scored[:limit]
                self._last_call_stats = {
                    "backend": "sqlite_fallback",
                    "hits": len(rows),
                    "limit": limit,
                    "elapsed_ms": int((time.perf_counter() - start) * 1000),
                }
                return rows
        except Exception as e:
            logger.warning("Vector search failed: %s", e)
            self._last_call_stats = {
                "backend": "error",
                "error": str(e),
                "elapsed_ms": int((time.perf_counter() - start) * 1000),
            }
            return []

    async def search_vectors_async(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """ベクトルストア非同期検索."""
        try:
            results = await self._vector_store.search(
                collection_name=collection_name,
                query_embedding=query_embedding,
                top_k=top_k,
                where=where,
            )
            return [
                SearchResult(
                    id=r.get("id", ""),
                    content=r.get("content", ""),
                    metadata=r.get("metadata", {}),
                    source="vector_store",
                    score=r.get("similarity", 0.0),
                    distance=r.get("distance"),
                    similarity=r.get("similarity"),
                )
                for r in results
            ]
        except Exception as e:
            logger.warning("Async vector search failed: %s", e)
            return []

    async def hybrid_search(
        self,
        session: Session,
        query: str,
        query_embedding: list[float] | None = None,
        core_entities: list[str] | None = None,
        top_k: int = 10,
        alpha: float = 0.5,  # Vector weight
        beta: float = 0.3,   # Graph weight
        gamma: float = 0.2,  # Fulltext weight
    ) -> list[SearchResult]:
        """ハイブリッド検索: Vector + Graph + Fulltext の RRF 融合.

        Args:
            session: DBセッション
            query: 検索クエリテキスト
            query_embedding: 事前計算済みクエリ埋め込み（Noneなら自動生成）
            core_entities: グラフ探索の起点エンティティ
            top_k: 返却件数
            alpha: ベクトル検索の重み
            beta: グラフ検索の重み
            gamma: 全文検索の重み
        """
        if query_embedding is None:
            query_embedding = embedding_service.get_embedding(query)

        # 正規化
        total = alpha + beta + gamma
        alpha, beta, gamma = alpha / total, beta / total, gamma / total

        start = time.perf_counter()
        all_results: dict[str, SearchResult] = {}

        # 1. ベクトル検索
        vector_results = self.search_similar_chunks(session, query, limit=top_k * 2)
        for i, r in enumerate(vector_results):
            rrf_score = alpha / (60 + i + 1)  # RRF: k=60
            all_results[r.id] = SearchResult(
                id=r.id,
                content=r.content,
                metadata=r.metadata,
                source="vector",
                score=rrf_score,
                distance=r.distance,
                similarity=r.similarity,
            )

        # 2. グラフ探索
        if core_entities and settings.ENABLE_GRAPHRAG and settings.DATABASE_URL.startswith("postgresql"):
            graph_results = self._search_graph(session, core_entities, query_embedding, top_k * 2)
            for i, r in enumerate(graph_results):
                rrf_score = beta / (60 + i + 1)
                if r.id in all_results:
                    all_results[r.id].score += rrf_score
                    all_results[r.id].source += "+graph"
                else:
                    r.score = rrf_score
                    all_results[r.id] = r

        # 3. 全文検索 (PostgreSQL tsvector)
        if settings.DATABASE_URL.startswith("postgresql"):
            text_results = self._search_fulltext(session, query, top_k * 2)
            for i, r in enumerate(text_results):
                rrf_score = gamma / (60 + i + 1)
                if r.id in all_results:
                    all_results[r.id].score += rrf_score
                    all_results[r.id].source += "+fulltext"
                else:
                    r.score = rrf_score
                    all_results[r.id] = r

        # スコア順ソート
        sorted_results = sorted(all_results.values(), key=lambda x: x.score, reverse=True)

        elapsed = (time.perf_counter() - start) * 1000
        self._last_call_stats = {
            "backend": "hybrid",
            "hits": len(sorted_results),
            "limit": top_k,
            "elapsed_ms": int(elapsed),
            "weights": {"vector": alpha, "graph": beta, "fulltext": gamma},
        }

        return sorted_results[:top_k]

    def _search_graph(
        self,
        session: Session,
        core_entities: list[str],
        query_embedding: list[float],
        limit: int,
    ) -> list[SearchResult]:
        """グラフ探索とセマンティック再ランキング."""
        results: list[SearchResult] = []
        for entity in core_entities:
            if not entity.strip():
                continue
            neighbors = age_client.get_neighbors(session, entity.strip(), max_depth=2)
            for item in neighbors:
                name = item.get("name", "")
                rel = item.get("relation_type", "")
                props = item.get("properties") or {}
                desc = props.get("description", "") if isinstance(props, dict) else ""

                fact_text = f"{name} {rel} {desc}".strip()
                item_emb = embedding_service.get_embedding(fact_text)
                sim = self._cosine_similarity(query_embedding, item_emb)

                # ユニークID生成
                result_id = f"graph_{entity}_{name}_{rel}".replace(" ", "_")

                results.append(SearchResult(
                    id=result_id,
                    content=f"[{rel}] {name}: {desc}" if desc else f"[{rel}] {name}",
                    metadata={
                        "entity": name,
                        "relation": rel,
                        "source_entity": entity,
                        "properties": props,
                    },
                    source="graph",
                    score=sim,
                    similarity=sim,
                ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def _search_fulltext(
        self,
        session: Session,
        query: str,
        limit: int,
    ) -> list[SearchResult]:
        """PostgreSQL 全文検索 (tsvector)."""
        try:
            # plainto_tsquery でクエリをパース
            stmt = text("""
                SELECT id, content, chunk_metadata,
                       ts_rank_cd(to_tsvector('simple', content), plainto_tsquery('simple', :query)) AS rank
                FROM chapter_chunks
                WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', :query)
                ORDER BY rank DESC
                LIMIT :limit
            """)
            result = session.execute(stmt, {"query": query, "limit": limit})
            rows = []
            for row in result:
                rows.append(SearchResult(
                    id=str(row.id),
                    content=row.content,
                    metadata=row.chunk_metadata or {},
                    source="fulltext",
                    score=float(row.rank) if row.rank else 0.0,
                ))
            return rows
        except Exception as e:
            logger.debug("Fulltext search failed: %s", e)
            return []

    def get_graph_context(
        self,
        session: Session,
        core_entities: list[str],
        max_depth: int = 2,
    ) -> list[dict[str, Any]]:
        """指定された主要エンティティから 1〜2 ホップ以内の確定相関情報を取得する."""
        if not settings.ENABLE_GRAPHRAG or not settings.DATABASE_URL.startswith("postgresql"):
            return []

        all_neighbors: list[dict[str, Any]] = []
        for name in core_entities:
            if not name or not name.strip():
                continue
            neighbors = age_client.get_neighbors(session, name.strip(), max_depth=max_depth)
            all_neighbors.extend(neighbors)

        return all_neighbors

    def rerank_graph_neighbors(
        self,
        neighbors: list[dict[str, Any]],
        current_prompt: str,
        top_k: int = 7,
    ) -> list[dict[str, Any]]:
        """プロンプトの意味ベクトルに基づき、取得したグラフ事実を関連度順に再評価 (Rerank) する."""
        if not neighbors or not current_prompt.strip():
            return neighbors[:top_k]

        prompt_emb = embedding_service.get_embedding(current_prompt)
        scored_neighbors = []

        for item in neighbors:
            name = item.get("name", "")
            rel = item.get("relation_type", "")
            props = item.get("properties") or {}
            desc = props.get("description", "") if isinstance(props, dict) else ""

            fact_text = f"{name} {rel} {desc}".strip()
            item_emb = embedding_service.get_embedding(fact_text)
            sim = self._cosine_similarity(prompt_emb, item_emb)
            scored_neighbors.append((sim, item))

        scored_neighbors.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored_neighbors[:top_k]]

    async def rerank_with_cross_encoder(
        self,
        query: str,
        documents: list[str],
        top_k: int = 5,
    ) -> list[tuple[int, float]]:
        """Cross-Encoder Reranker で再ランキング."""
        if not documents:
            return []
        reranker = self.get_reranker()
        return await reranker.rerank(query, documents, top_k)

    def _cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """2つのベクトルのコサイン類似度を計算する."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def _estimate_tokens(self, text: str) -> int:
        """概算トークン数（日本語: 文字数/1.5, 英語: 単語数*1.3）."""
        ja_chars = sum(1 for c in text if ord(c) > 0x3000)
        en_words = len(text.split())
        return int(ja_chars / 1.5 + en_words * 1.3)

    def _truncate_to_budget(self, texts: list[str], budget: int) -> list[str]:
        """トークン予算内に収まるよう切り詰め."""
        result = []
        used = 0
        for t in texts:
            tokens = self._estimate_tokens(t)
            if used + tokens > budget:
                # 残り予算で切り詰め
                remaining = budget - used
                if remaining > 50:
                    # 日本語優先で切り詰め
                    result.append(t[:int(remaining * 1.5)] + "...")
                break
            result.append(t)
            used += tokens
        return result

    async def build_rag_context(
        self,
        session: Session,
        current_prompt: str,
        character_name: str,
        additional_entities: list[str] | None = None,
        *,
        use_cache: bool = True,
    ) -> RagContext:
        """小説執筆プロンプトに注入するハイブリッドコンテキストを生成.

        Returns:
            RagContext: グラフ/ベクトル/全文コンテキストと統計
        """
        cache_key = self._get_cache_key("rag_ctx", current_prompt, character_name, str(additional_entities))
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached:
                logger.debug("RAG context cache hit")
                return cached

        start = time.perf_counter()

        # 1. 主要エンティティの特定
        entities_to_query = [character_name]
        if additional_entities:
            entities_to_query.extend(additional_entities)

        # 2. グラフ探索と Reranking
        neighbors = self.get_graph_context(session, entities_to_query, max_depth=2)
        if neighbors:
            ranked_neighbors = self.rerank_graph_neighbors(neighbors, current_prompt, top_k=7)
            graph_lines = []
            for item in ranked_neighbors:
                name = item.get("name")
                rel = item.get("relation_type") or "関係あり"
                props = item.get("properties") or {}
                desc = ""
                if isinstance(props, dict) and "description" in props:
                    desc = f" ({props['description']})"
                graph_lines.append(f"- 【{name}】: {rel}{desc}")
            graph_context = "\n".join(graph_lines)
        else:
            graph_context = "- 確定された特記事項なし（初期状態）"

        # 3. ハイブリッド検索 (ベクトル + グラフ + 全文)
        query_embedding = embedding_service.get_embedding(current_prompt)
        hybrid_results = await self.hybrid_search(
            session, current_prompt, query_embedding, entities_to_query, top_k=5
        )

        if hybrid_results:
            vector_lines = []
            for i, r in enumerate(hybrid_results):
                source_tag = f"[{r.source}]"
                vector_lines.append(f"{source_tag} 参照{i+1}:\n{r.content}")
            vector_context = "\n\n".join(vector_lines)
        else:
            vector_context = "なし（関連情報なし）"

        # 4. トークン予算内に調整
        graph_context = "\n".join(self._truncate_to_budget(graph_context.split("\n"), self._token_budget // 3))
        vector_context = "\n\n".join(self._truncate_to_budget(vector_context.split("\n\n"), self._token_budget * 2 // 3))

        stats = self.get_last_stats()
        stats["total_elapsed_ms"] = int((time.perf_counter() - start) * 1000)

        context = RagContext(
            graph_context=graph_context,
            vector_context=vector_context,
            fulltext_context="",  # ハイブリッドに統合済み
            stats=stats,
            token_estimate=self._estimate_tokens(graph_context + vector_context),
        )

        if use_cache:
            self._set_cache(cache_key, context)

        return context

    def get_community_context(
        self,
        session: Session,
        core_faction: str = "主人公派閥",
    ) -> list[str]:
        """派閥（コミュニティ）に所属するメンバー一覧と関係性を抽出する."""
        if not settings.ENABLE_GRAPHRAG or not settings.DATABASE_URL.startswith("postgresql"):
            return []

        neighbors = age_client.get_neighbors(session, core_faction, max_depth=1)
        faction_members = []
        for item in neighbors:
            name = item.get("name", "")
            rel = item.get("relation_type", "")
            if name:
                faction_members.append(f"{name} ({rel})")
        return faction_members

    def retrieve_for_episode(
        self,
        session: Session,
        *,
        book_id: int | None = None,
        episode_number: int | None = None,
        character_name: str,
        additional_entities: list[str] | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """エピソード執筆向けにハイブリッド検索結果を一括取得する公開 API."""
        current_prompt = character_name
        if episode_number is not None:
            current_prompt = f"{character_name} ep{episode_number}"

        context = self.build_rag_context(
            session,
            current_prompt=current_prompt,
            character_name=character_name,
            additional_entities=additional_entities,
        )

        return {
            "graph": context.graph_context,
            "vector": context.vector_context,
            "fulltext": context.fulltext_context,
            "stats": context.stats,
            "token_estimate": context.token_estimate,
            "book_id": book_id,
            "episode_number": episode_number,
            "top_k": top_k,
        }

    def clear_cache(self) -> None:
        """キャッシュクリア."""
        self._cache.clear()


rag_service = GraphRAGService()

__all__ = [
    "GraphRAGService",
    "rag_service",
    "Reranker",
    "SearchResult",
    "RagContext",
]
