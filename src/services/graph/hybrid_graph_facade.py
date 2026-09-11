"""ハイブリッドグラフファサード.

ENABLE_GRAPHRAG=true かつ PostgreSQL/AGE 接続可能なら AGE を使用し、
接続不可または SQLite 時は自動で NetworkXGraphStore にフォールバックする。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.backend.config import settings
from src.services.graph.base import (
    CentralityScores,
    GraphEdge,
    GraphKnowledgeStore,
    GraphNode,
    GraphStats,
    NeighborResult,
    PathResult,
)
from src.services.graph.networkx_store import NetworkXGraphStore

logger = logging.getLogger("hybrid_graph_facade")


class HybridGraphFacade(GraphKnowledgeStore):
    """ハイブリッドグラフファサード.

    バックエンドストアを自動選択:
    - PostgreSQL + Apache AGE 利用可能: AgeClient
    - それ以外: NetworkXGraphStore (SQLite/インメモリ)
    """

    def __init__(
        self,
        default_graph_name: str | None = None,
        sqlite_path: str | None = None,
        session: Session | None = None,
    ) -> None:
        self._default_graph_name = default_graph_name or settings.AGE_GRAPH_NAME
        self._sqlite_path = sqlite_path or str(Path(settings.DATABASE_URL.replace("sqlite:///", "")).with_suffix(".graph.db"))
        self._session = session
        self._age_client: Any = None
        self._nx_store: NetworkXGraphStore | None = None
        self._backend: str = "unknown"
        self._initialized = False

    def _ensure_initialized(self, session: Session | None = None) -> None:
        """バックエンドを初期化する."""
        if self._initialized:
            return

        sess = session or self._session
        if sess is not None and self._can_use_age(sess):
            try:
                # Lazy import to avoid circular dependency
                from src.services.age_client import AgeClient
                self._age_client = AgeClient(default_graph_name=self._default_graph_name, auto_init=True)
                if self._age_client.init_graph(sess):
                    self._backend = "age"
                    logger.info("Using Apache AGE backend for graph operations")
                    self._initialized = True
                    return
            except Exception as e:
                logger.warning("Failed to initialize AGE backend, falling back to NetworkX: %s", e)

        self._nx_store = NetworkXGraphStore(sqlite_path=self._sqlite_path)
        self._backend = "networkx"
        logger.info("Using NetworkX backend for graph operations (SQLite: %s)", self._sqlite_path)
        self._initialized = True

    def _can_use_age(self, session: Session) -> bool:
        """AGE が利用可能かチェックする."""
        if not settings.ENABLE_GRAPHRAG:
            return False
        if not settings.DATABASE_URL.startswith("postgresql"):
            return False
        try:
            bind = session.get_bind()
            if bind is None:
                return False
            dialect = bind.dialect.name if hasattr(bind, 'dialect') else ""
            return dialect == "postgresql"
        except Exception:
            return False

    @property
    def backend(self) -> str:
        """現在のバックエンド名を返す."""
        return self._backend

    @property
    def is_using_age(self) -> bool:
        """AGE を使用中かどうか."""
        return self._backend == "age"

    @property
    def is_using_networkx(self) -> bool:
        """NetworkX を使用中かどうか."""
        return self._backend == "networkx"

    def _get_store(self) -> GraphKnowledgeStore:
        """実際のストア実装を取得する."""
        if self._backend == "age" and self._age_client:
            return self._age_client
        if self._nx_store:
            return self._nx_store
        raise RuntimeError("No backend available")

    def _get_age_session(self) -> Session | None:
        """AGE 用セッションを取得する."""
        return self._session

    def add_entity(
        self,
        label: str,
        name: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        if self._backend == "age" and self._age_client:
            sess = self._get_age_session()
            if sess:
                return self._age_client.upsert_node(sess, label, name, properties)
            return False
        store = self._get_store()
        return store.add_entity(label, name, properties)

    def add_relation(
        self,
        source_label: str,
        source_name: str,
        target_label: str,
        target_name: str,
        relation_type: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        if self._backend == "age" and self._age_client:
            sess = self._get_age_session()
            if sess:
                return self._age_client.upsert_edge(
                    sess, source_label, source_name, target_label, target_name, relation_type, properties
                )
            return False
        store = self._get_store()
        return store.add_relation(source_label, source_name, target_label, target_name, relation_type, properties)

    def find_neighbors(
        self,
        entity_id: str,
        hops: int = 2,
        relationship_types: list[str] | None = None,
        direction: str = "both",
        limit: int = 50,
    ) -> NeighborResult:
        if self._backend == "age" and self._age_client:
            sess = self._get_age_session()
            if sess:
                neighbors = self._age_client.get_neighbors(
                    sess, entity_id, max_depth=hops,
                    relationship_types=relationship_types, direction=direction, limit=limit
                )
                return NeighborResult(
                    nodes=[
                        GraphNode(
                            id=n["name"],
                            label=n["labels"] if isinstance(n["labels"], str) else n["labels"][0] if n["labels"] else "Entity",
                            name=n["name"],
                            properties=n.get("properties", {}),
                        )
                        for n in neighbors
                    ],
                    edges=[
                        GraphEdge(
                            source=entity_id,
                            target=n["name"],
                            relation_type=n.get("relation_type", "RELATED_TO"),
                            properties=n.get("properties", {}),
                        )
                        for n in neighbors
                    ],
                    depth=hops,
                )
        store = self._get_store()
        return store.find_neighbors(entity_id, hops, relationship_types, direction, limit)

    def find_shortest_path(
        self,
        source_name: str,
        target_name: str,
        max_depth: int = 5,
    ) -> PathResult | None:
        if self._backend == "age" and self._age_client:
            sess = self._get_age_session()
            if sess:
                path = self._age_client.get_shortest_path(sess, source_name, target_name, max_depth)
                if path:
                    return PathResult(
                        nodes=path.get("nodes", []),
                        edges=path.get("edges", []),
                        length=path.get("length", 0),
                    )
                return None
        store = self._get_store()
        return store.find_shortest_path(source_name, target_name, max_depth)

    def get_centrality(self) -> CentralityScores:
        if self._backend == "age" and self._age_client:
            pass
        store = self._get_store()
        return store.get_centrality()

    def get_all_nodes(
        self,
        limit: int = 5000,
        labels: list[str] | None = None,
    ) -> list[GraphNode]:
        if self._backend == "age" and self._age_client:
            sess = self._get_age_session()
            if sess:
                rows = self._age_client.get_all_nodes(sess, limit=limit, labels=labels)
                return [
                    GraphNode(
                        id=r["name"],
                        label=r["labels"] if isinstance(r["labels"], str) else (r["labels"][0] if r["labels"] else "Entity"),
                        name=r["name"],
                        properties=r.get("properties", {}),
                    )
                    for r in rows
                ]
        store = self._get_store()
        return store.get_all_nodes(limit, labels)

    def get_all_edges(
        self,
        limit: int = 10000,
    ) -> list[GraphEdge]:
        if self._backend == "age" and self._age_client:
            pass
        store = self._get_store()
        return store.get_all_edges(limit)

    def get_stats(self) -> GraphStats:
        if self._backend == "age" and self._age_client:
            sess = self._get_age_session()
            if sess:
                stats = self._age_client.get_graph_stats(sess)
                return GraphStats(
                    node_count=stats.node_count,
                    edge_count=stats.edge_count,
                    labels=stats.labels,
                    relationship_types=stats.relationship_types,
                )
        store = self._get_store()
        return store.get_stats()

    def delete_node(
        self,
        label: str,
        name: str,
        detach: bool = True,
    ) -> bool:
        if self._backend == "age" and self._age_client:
            sess = self._get_age_session()
            if sess:
                return self._age_client.delete_node(sess, label, name, detach=detach)
            return False
        store = self._get_store()
        return store.delete_node(label, name, detach)

    def delete_edge(
        self,
        source_label: str,
        source_name: str,
        target_label: str,
        target_name: str,
        relation_type: str,
    ) -> bool:
        if self._backend == "age" and self._age_client:
            sess = self._get_age_session()
            if sess:
                return self._age_client.delete_edge(sess, source_label, source_name, target_label, target_name, relation_type)
            return False
        store = self._get_store()
        return store.delete_edge(source_label, source_name, target_label, target_name, relation_type)

    def clear(self) -> None:
        if self._backend == "age" and self._age_client:
            pass
        store = self._get_store()
        store.clear()

    def save_to_sqlite(self, db_path: str) -> bool:
        if self._backend == "networkx" and self._nx_store:
            return self._nx_store.save_to_sqlite(db_path)
        return False

    def load_from_sqlite(self, db_path: str) -> bool:
        if self._backend == "networkx" and self._nx_store:
            return self._nx_store.load_from_sqlite(db_path)
        return False

    def is_available(self) -> bool:
        return True

    def execute_cypher(
        self,
        session: Session,
        cypher_query: str,
        column_definition: str = "(result agtype)",
        graph_name: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> CypherResult:
        """Cypher クエリを実行する (AGE バックエンド時のみ)."""
        if self._backend == "age" and self._age_client:
            return self._age_client.execute_cypher(
                session, cypher_query, column_definition, graph_name, parameters
            )
        raise RuntimeError("Cypher execution only available with AGE backend")

    def get_age_client(self) -> AgeClient | None:
        """AgeClient インスタンスを取得する (AGE バックエンド時のみ)."""
        return self._age_client if self._backend == "age" else None

    def get_networkx_store(self) -> NetworkXGraphStore | None:
        """NetworkXGraphStore インスタンスを取得する (NetworkX バックエンド時のみ)."""
        return self._nx_store if self._backend == "networkx" else None


_hybrid_facade: HybridGraphFacade | None = None


def get_hybrid_facade(
    default_graph_name: str | None = None,
    sqlite_path: str | None = None,
    session: Session | None = None,
) -> HybridGraphFacade:
    """HybridGraphFacade シングルトンインスタンスを取得する."""
    global _hybrid_facade
    if _hybrid_facade is None:
        _hybrid_facade = HybridGraphFacade(default_graph_name, sqlite_path, session)
    return _hybrid_facade


def reset_hybrid_facade() -> None:
    """シングルトンインスタンスをリセットする (テスト用)."""
    global _hybrid_facade
    _hybrid_facade = None