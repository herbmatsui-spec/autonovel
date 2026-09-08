"""
src/services/vector_store/pgvector.py - PostgreSQL + pgvector ベクトルストア実装
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any
from contextlib import asynccontextmanager

from src.services.vector_store.base import (
    BaseVectorStore,
    CollectionType,
    CollectionConfig,
    DEFAULT_COLLECTIONS,
)

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    HAS_PGVECTOR = True
except Exception as e:
    logger.warning(f"[VECTOR STORE] Failed to import pgvector/sqlalchemy: {e}.")
    HAS_PGVECTOR = False

def _embedding_to_pgvector(emb: list[float]) -> str:
    """Convert embedding list to pgvector string format."""
    return "[" + ", ".join(str(x) for x in emb) + "]"


class PgVectorStore(BaseVectorStore):
    """
    PostgreSQL + pgvector を使用したベクトルデータベース管理クラス。
    HNSW/IVFFlat インデックスを使用した高速類似度検索を提供する。
    """

    def __init__(
        self,
        database_url: str,
        *,
        dimension: int = 1536,
        pool_size: int = 10,
        max_overflow: int = 20,
    ) -> None:
        if not HAS_PGVECTOR:
            raise RuntimeError("pgvector is not installed. Install with: pip install pgvector")

        self.database_url = database_url
        self.dimension = dimension
        
        async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        self._engine = create_async_engine(
            async_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine, class_=AsyncSession, expire_on_commit=False
        )
        self._initialized_tables: set[str] = set()

    async def _get_session(self) -> AsyncSession:
        """Create a new session. Use as: session = await self._get_session()"""
        return self._session_factory()

    @asynccontextmanager
    async def _session(self):
        """Context manager for session. Use as: async with self._session() as session:"""
        async with self._session_factory() as session:
            yield session

    @staticmethod
    def _validate_metadata_key(key: str) -> str:
        """メタデータキーが英数字・アンダースコアのみで構成されているか検証（SQLインジェクション対策）."""
        if not re.fullmatch(r"[a-zA-Z0-9_]{1,64}", key):
            raise ValueError(f"Invalid metadata key: '{key}'. Must be alphanumeric and underscore only, max 64 chars.")
        return key

    def _get_table_name(self, collection_name: str) -> str:
        """コレクション名からテーブル名を生成（サニタイズ・検証）."""
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", collection_name).strip("_")
        if not safe_name:
            safe_name = "default"
        # PostgreSQLの識別子長制限（通常63バイト）を考慮
        safe_name = safe_name[:48]
        if not re.fullmatch(r"[a-zA-Z0-9_]+", safe_name):
            raise ValueError(f"Invalid collection name after sanitization: '{collection_name}'")
        return f"vec_{safe_name}"

    async def _ensure_table(self, collection_name: str, space: str = "cosine") -> bool:
        """テーブルとインデックスの存在確認・作成."""
        if collection_name in self._initialized_tables:
            return True

        table_name = self._get_table_name(collection_name)
        async with self._session() as session:
            try:
                # pgvector拡張の確認
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

                # テーブル作成
                create_table_sql = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        embedding vector({self.dimension}),
                        metadata JSONB DEFAULT '{{}}',
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """
                await session.execute(text(create_table_sql))

                # HNSWインデックス作成（cosine距離用）
                index_name = f"idx_{table_name}_embedding_hnsw"
                create_index_sql = f"""
                    CREATE INDEX IF NOT EXISTS {index_name}
                    ON {table_name} USING hnsw (embedding vector_cosine_ops)
                    WITH (m = 16, ef_construction = 100);
                """
                await session.execute(text(create_index_sql))

                # メタデータ用GINインデックス
                metadata_index = f"idx_{table_name}_metadata_gin"
                await session.execute(
                    text(f"""
                    CREATE INDEX IF NOT EXISTS {metadata_index}
                    ON {table_name} USING gin (metadata);
                """)
                )

                await session.commit()
                self._initialized_tables.add(collection_name)
                logger.info(f"[PGVECTOR STORE] Initialized table '{table_name}' with HNSW index")
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"[PGVECTOR STORE] Failed to initialize table '{table_name}': {e}")
                return False

    async def add_documents(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """ドキュメントをベクトルDBに追加する (バッチINSERT)."""
        if not ids:
            return

        await self._ensure_table(collection_name)
        table_name = self._get_table_name(collection_name)

        # バッチサイズ制限（PostgreSQLのパラメータ制限考慮）
        batch_size = 100
        total = len(ids)

        async with self._session() as session:
            try:
                for start in range(0, total, batch_size):
                    end = min(start + batch_size, total)
                    batch_ids = ids[start:end]
                    batch_docs = documents[start:end]
                    batch_embs = embeddings[start:end]
                    batch_metas = (
                        metadatas[start:end] if metadatas else [{} for _ in range(end - start)]
                    )

                    # UPSERT (ON CONFLICT DO UPDATE)
                    values = []
                    params = {}
                    for i, (doc_id, doc, emb, meta) in enumerate(
                        zip(batch_ids, batch_docs, batch_embs, batch_metas)
                    ):
                        param_prefix = f"doc{start + i}"
                        values.append(
                            f"(:{param_prefix}_id, :{param_prefix}_content, :{param_prefix}_emb, :{param_prefix}_meta)"
                        )
                        params[f"{param_prefix}_id"] = doc_id
                        params[f"{param_prefix}_content"] = doc
                        params[f"{param_prefix}_emb"] = _embedding_to_pgvector(emb)
                        params[f"{param_prefix}_meta"] = json.dumps(meta, ensure_ascii=False)

                    values_sql = ", ".join(values)
                    upsert_sql = f"""
                        INSERT INTO {table_name} (id, content, embedding, metadata)
                        VALUES {values_sql}
                        ON CONFLICT (id) DO UPDATE SET
                            content = EXCLUDED.content,
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata;
                    """
                    await session.execute(text(upsert_sql), params)

                await session.commit()
                logger.info(f"[PGVECTOR STORE] Added {total} documents to table '{table_name}'")
            except Exception as e:
                await session.rollback()
                logger.error(f"[PGVECTOR STORE] Failed to add documents to '{table_name}': {e}")
                raise

    async def search(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """ベクトル類似度検索を実行する (コサイン距離)."""
        table_name = self._get_table_name(collection_name)
        await self._ensure_table(collection_name)

        async with self._session() as session:
            try:
                # WHERE句の構築（メタデータフィルタ）
                where_clause = ""
                params: dict[str, Any] = {"query_emb": _embedding_to_pgvector(query_embedding), "limit": top_k}

                if where:
                    conditions = []
                    for i, (key, value) in enumerate(where.items()):
                        valid_key = self._validate_metadata_key(key)
                        param_key = f"meta_{i}"
                        conditions.append(f"metadata->>'{valid_key}' = :{param_key}")
                        params[param_key] = str(value)
                    where_clause = "WHERE " + " AND ".join(conditions)

                search_sql = f"""
                    SELECT id, content, metadata, embedding <=> :query_emb AS distance
                    FROM {table_name}
                    {where_clause}
                    ORDER BY embedding <=> :query_emb
                    LIMIT :limit;
                """

                result = await session.execute(text(search_sql), params)
                rows = result.fetchall()

                output = []
                for row in rows:
                    if isinstance(row, (tuple, list)):
                        r_id, r_content, r_meta, r_dist = row[0], row[1], row[2], row[3]
                    else:
                        r_id = getattr(row, "id", row[0])
                        r_content = getattr(row, "content", row[1])
                        r_meta = getattr(row, "metadata", row[2])
                        r_dist = getattr(row, "distance", row[3])
                    distance = float(r_dist) if r_dist is not None else 1.0
                    similarity = 1.0 - distance
                    output.append(
                        {
                            "id": r_id,
                            "content": r_content,
                            "metadata": r_meta if isinstance(r_meta, dict) else {},
                            "distance": distance,
                            "similarity": similarity,
                        }
                    )
                return output
            except Exception as e:
                logger.error(f"[PGVECTOR STORE] Search failed for '{table_name}': {e}")
                return []

    async def search_with_score(
        self,
        collection_name: str,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """スコア閾値付き検索（コサイン類似度ベース）."""
        results = await self.search(collection_name, query_embedding, top_k, where)

        filtered = []
        for r in results:
            similarity = r.get("similarity", 0.0)
            if similarity >= min_score:
                r["similarity"] = similarity
                filtered.append(r)

        filtered.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return filtered

    async def delete_by_id(self, collection_name: str, ids: list[str]) -> None:
        """指定したIDのドキュメントを削除する."""
        if not ids:
            return

        table_name = self._get_table_name(collection_name)
        async with self._session() as session:
            try:
                # バッチ削除
                placeholders = ", ".join(f":id_{i}" for i in range(len(ids)))
                params = {f"id_{i}": id_val for i, id_val in enumerate(ids)}
                delete_sql = f"DELETE FROM {table_name} WHERE id IN ({placeholders});"
                await session.execute(text(delete_sql), params)
                await session.commit()
                logger.info(f"[PGVECTOR STORE] Deleted {len(ids)} documents from '{table_name}'")
            except Exception as e:
                await session.rollback()
                logger.error(f"[PGVECTOR STORE] Failed to delete from '{table_name}': {e}")
                raise

    async def clear_collection(self, collection_name: str) -> None:
        """コレクション（テーブル）を空にする."""
        table_name = self._get_table_name(collection_name)
        async with self._session() as session:
            try:
                await session.execute(text(f"TRUNCATE TABLE {table_name};"))
                await session.commit()
                logger.info(f"[PGVECTOR STORE] Cleared table '{table_name}'")
            except Exception as e:
                await session.rollback()
                logger.error(f"[PGVECTOR STORE] Failed to clear '{table_name}': {e}")
                raise

    async def get_collection_stats(self, collection_name: str) -> dict[str, Any]:
        """コレクションの統計情報を取得."""
        table_name = self._get_table_name(collection_name)
        async with self._session() as session:
            try:
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table_name};"))
                count = result.scalar() or 0
                return {"count": count, "name": collection_name, "table": table_name}
            except Exception as e:
                logger.error(f"[PGVECTOR STORE] Failed to get stats for '{table_name}': {e}")
                return {"count": 0, "error": str(e)}

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
        """
        ハイブリッド検索: ベクトル類似度検索 + 全文検索 (tsvector)

        PostgreSQLのtsvectorを使用したキーワード検索とベクトル検索を統合。
        """
        if alpha < 0.0 or alpha > 1.0:
            logger.warning(f"[PGVECTOR STORE] hybrid_search alpha={alpha} out of [0,1], clamping.")
            alpha = max(0.0, min(1.0, alpha))

        table_name = self._get_table_name(collection_name)
        await self._ensure_table(collection_name)

        # ベクトル検索（より多く取得して後でフィルタリング）
        vector_results = await self.search_with_score(
            collection_name, query_embedding, top_k * 3, where, min_score=0.0
        )

        # 全文検索 (tsvector)
        text_results = []
        async with self._session() as session:
            try:
                # tsvector検索用クエリ
                # plainto_tsqueryでクエリをパース
                where_clause = ""
                params = {"query_text": query_text, "limit": top_k * 3}

                if where:
                    conditions = []
                    for i, (key, value) in enumerate(where.items()):
                        valid_key = self._validate_metadata_key(key)
                        param_key = f"meta_{i}"
                        conditions.append(f"metadata->>'{valid_key}' = :{param_key}")
                        params[param_key] = str(value)
                    where_clause = "AND " + " AND ".join(conditions)

                text_search_sql = f"""
                    SELECT id, content, metadata,
                           ts_rank_cd(to_tsvector('simple', content), plainto_tsquery('simple', :query_text)) AS rank
                    FROM {table_name}
                    WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', :query_text)
                    {where_clause}
                    ORDER BY rank DESC
                    LIMIT :limit;
                """

                result = await session.execute(text(text_search_sql), params)
                rows = result.fetchall()

                for row in rows:
                    if isinstance(row, (tuple, list)):
                        r_id, r_content, r_meta, r_rank = row[0], row[1], row[2], row[3]
                    else:
                        r_id = getattr(row, "id", row[0])
                        r_content = getattr(row, "content", row[1])
                        r_meta = getattr(row, "metadata", row[2])
                        r_rank = getattr(row, "rank", row[3])
                    text_results.append(
                        {
                            "id": r_id,
                            "content": r_content,
                            "metadata": r_meta if isinstance(r_meta, dict) else {},
                            "rank": float(r_rank) if r_rank else 0.0,
                        }
                    )
            except Exception as e:
                logger.debug(f"[PGVECTOR STORE] Full-text search failed: {e}")

        # 結果を結合（RRF - Reciprocal Rank Fusion）
        return self._fuse_results(vector_results, text_results, top_k, alpha, min_score)

    def _fuse_results(
        self,
        vector_results: list[dict[str, Any]],
        text_results: list[dict[str, Any]],
        top_k: int,
        alpha: float,
        min_score: float,
    ) -> list[dict[str, Any]]:
        """ベクトル検索と全文検索の結果をRRFで融合."""
        # IDでマップ化
        vector_map = {r["id"]: r for r in vector_results}
        text_map = {r["id"]: r for r in text_results}
        all_ids = set(vector_map.keys()) | set(text_map.keys())

        # ランキング計算
        vector_rank = {r["id"]: i + 1 for i, r in enumerate(vector_results)}
        text_rank = {r["id"]: i + 1 for i, r in enumerate(text_results)}

        combined = []
        k = 60  # RRF定数

        for doc_id in all_ids:
            v_result = vector_map.get(doc_id)
            t_result = text_map.get(doc_id)

            # RRFスコア計算
            v_rank = vector_rank.get(doc_id, len(vector_results) + 1)
            t_rank = text_rank.get(doc_id, len(text_results) + 1)

            rrf_score = (alpha / (k + v_rank)) + ((1 - alpha) / (k + t_rank))

            if rrf_score >= min_score:
                # ベクトル検索のメタデータを優先
                metadata = v_result.get("metadata", {}) if v_result else {}
                if not metadata and t_result:
                    metadata = t_result.get("metadata", {})

                combined.append(
                    {
                        "id": doc_id,
                        "content": v_result.get("content")
                        if v_result
                        else (t_result.get("content", "") if t_result else ""),
                        "metadata": metadata,
                        "vector_similarity": v_result.get("similarity", 0.0) if v_result else 0.0,
                        "text_rank": t_result.get("rank", 0.0) if t_result else 0.0,
                        "rrf_score": rrf_score,
                    }
                )

        combined.sort(key=lambda x: x["rrf_score"], reverse=True)
        return combined[:top_k]

    async def close(self) -> None:
        """エンジンを閉じる."""
        await self._engine.dispose()
        logger.info("[PGVECTOR STORE] Engine disposed")




__all__ = ["PgVectorStore", "HAS_PGVECTOR", "_embedding_to_pgvector"]
