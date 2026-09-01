"""GraphRAG 検索・コンテキスト構築サービスモジュール (ハイブリッド Reranking 対応)."""
from __future__ import annotations

import math
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.backend.config import settings
from src.backend.logging_config import get_logger
from src.infrastructure.database.models.chunk import HAS_PGVECTOR, ChapterChunk
from src.services.age_client import age_client
from src.services.embedding_service import embedding_service

logger = get_logger("rag_service")


class GraphRAGService:
    """ベクトル検索とナレッジグラフ探索を組み合わせたハイブリッドRAGサービス (Reranking対応)."""

    def search_similar_chunks(
        self,
        session: Session,
        query: str,
        limit: int = 3,
    ) -> list[str]:
        """クエリテキストに類似する過去の章チャンクを検索する."""
        if not query or not query.strip():
            return []

        try:
            # PostgreSQL + pgvector 環境
            if HAS_PGVECTOR and settings.DATABASE_URL.startswith("postgresql"):
                query_vector = embedding_service.get_embedding(query)
                # pgvector のコサイン距離演算子 (<=>) による順序づけ
                stmt = text(
                    """
                    SELECT content FROM chapter_chunks
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> :query_vector
                    LIMIT :limit
                    """
                )
                result = session.execute(stmt, {"query_vector": str(query_vector), "limit": limit})
                return [row[0] for row in result]
            else:
                # SQLite またはフォールバック: 最新チャンクから類似度順に並べ替え
                chunks = (
                    session.query(ChapterChunk)
                    .order_by(ChapterChunk.created_at.desc())
                    .limit(limit * 3)
                    .all()
                )
                if not chunks:
                    return []

                query_emb = embedding_service.get_embedding(query)
                scored: list[tuple[float, str]] = []
                for c in chunks:
                    chunk_text = str(c.content) if c.content is not None else ""
                    if not chunk_text:
                        continue
                    c_emb = embedding_service.get_embedding(chunk_text)
                    sim = self._cosine_similarity(query_emb, c_emb)
                    scored.append((sim, chunk_text))

                scored.sort(key=lambda x: x[0], reverse=True)
                return [content for _, content in scored[:limit]]
        except Exception as e:
            logger.warning("Vector search failed, falling back: %s", e)
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

        # 類似度の降順でソート
        scored_neighbors.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored_neighbors[:top_k]]

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

    def build_rag_context(
        self,
        session: Session,
        current_prompt: str,
        character_name: str,
        additional_entities: list[str] | None = None,
    ) -> tuple[str, str]:
        """小説執筆プロンプトに注入する (グラフコンテキスト, ベクトルコンテキスト) をハイブリッド生成する.

        Returns:
            (graph_context_text, vector_context_text)
        """
        # 1. 主要エンティティの特定
        entities_to_query = [character_name]
        if additional_entities:
            entities_to_query.extend(additional_entities)

        # 2. グラフ探索とハイブリッド Reranking
        neighbors = self.get_graph_context(session, entities_to_query)
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

        # 3. ベクトル検索 (伏線・類似過去シーン)
        similar_chunks = self.search_similar_chunks(session, current_prompt, limit=2)
        if similar_chunks:
            vector_lines = [f"[過去の重要シーン {i+1}]:\n{chunk}" for i, chunk in enumerate(similar_chunks)]
            vector_context = "\n\n".join(vector_lines)
        else:
            vector_context = "なし（第1話または関連シーンなし）"

        return graph_context, vector_context



rag_service = GraphRAGService()

__all__ = ["GraphRAGService", "rag_service"]
