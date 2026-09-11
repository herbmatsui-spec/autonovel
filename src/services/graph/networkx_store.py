"""NetworkX ベースのグラフエンジン実装 (Pure Python / SQLite 対応).

PostgreSQL や Apache AGE 拡張が一切ないローカル環境でも、
高速なマルチ有向グラフ探索を提供する。
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import networkx as nx

from src.services.graph.base import (
    CentralityScores,
    GraphEdge,
    GraphKnowledgeStore,
    GraphNode,
    GraphStats,
    NeighborResult,
    PathResult,
)


class NetworkXGraphStore(GraphKnowledgeStore):
    """Pure Python / NetworkX グラフエンジン.

    nx.MultiDiGraph を使用してマルチ有向グラフを管理。
    SQLite への永続化・復元をサポート。
    """

    def __init__(self, sqlite_path: str | None = None) -> None:
        """初期化.

        Args:
            sqlite_path: SQLite DB パス (None の場合はインメモリのみ)
        """
        self._graph = nx.MultiDiGraph()
        self._sqlite_path = sqlite_path

    def add_entity(
        self,
        label: str,
        name: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """エンティティ (ノード) を追加または更新する."""
        try:
            props = properties or {}
            props["label"] = label
            props["name"] = name
            self._graph.add_node(name, **props)
            return True
        except Exception:
            return False

    def add_relation(
        self,
        source_label: str,
        source_name: str,
        target_label: str,
        target_name: str,
        relation_type: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """リレーション (エッジ) を追加または更新する."""
        try:
            if not self._graph.has_node(source_name):
                self._graph.add_node(source_name, label=source_label, name=source_name)
            if not self._graph.has_node(target_name):
                self._graph.add_node(target_name, label=target_label, name=target_name)

            props = properties or {}
            props["relation_type"] = relation_type.upper()
            self._graph.add_edge(source_name, target_name, **props)
            return True
        except Exception:
            return False

    def find_neighbors(
        self,
        entity_id: str,
        hops: int = 2,
        relationship_types: list[str] | None = None,
        direction: str = "both",
        limit: int = 50,
    ) -> NeighborResult:
        """指定エンティティから N ホップ以内の近傍を探索する."""
        if entity_id not in self._graph:
            return NeighborResult(nodes=[], edges=[], depth=0)

        rel_types = {rt.upper() for rt in relationship_types} if relationship_types else None

        if direction == "outgoing":
            reach_nodes = nx.bfs_tree(self._graph, entity_id, depth_limit=hops).nodes()
        elif direction == "incoming":
            reach_nodes = nx.bfs_tree(self._graph.reverse(), entity_id, depth_limit=hops).nodes()
        else:
            undirected = self._graph.to_undirected()
            reach_nodes = nx.bfs_tree(undirected, entity_id, depth_limit=hops).nodes()

        subgraph = self._graph.subgraph(reach_nodes)

        nodes = []
        for node_id in subgraph.nodes():
            data = self._graph.nodes[node_id]
            nodes.append(GraphNode(
                id=node_id,
                label=data.get("label", "Entity"),
                name=data.get("name", node_id),
                properties={k: v for k, v in data.items() if k not in ("label", "name")},
            ))

        edges = []
        for u, v, k, data in subgraph.edges(keys=True, data=True):
            if rel_types and data.get("relation_type", "").upper() not in rel_types:
                continue
            if len(edges) >= limit:
                break
            edges.append(GraphEdge(
                source=u,
                target=v,
                relation_type=data.get("relation_type", "RELATED_TO"),
                properties={k: v for k, v in data.items() if k != "relation_type"},
            ))

        return NeighborResult(
            nodes=nodes[:limit],
            edges=edges[:limit],
            depth=hops,
        )

    def find_shortest_path(
        self,
        source_name: str,
        target_name: str,
        max_depth: int = 5,
    ) -> PathResult | None:
        """2ノード間の最短パスを探索する."""
        if source_name not in self._graph or target_name not in self._graph:
            return None

        try:
            path = nx.shortest_path(self._graph, source_name, target_name)
            if len(path) - 1 > max_depth:
                return None

            edges = []
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                edge_data = self._graph.get_edge_data(u, v)
                if edge_data:
                    first_key = next(iter(edge_data))
                    rel_type = edge_data[first_key].get("relation_type", "RELATED_TO")
                    edges.append((u, rel_type, v))

            return PathResult(
                nodes=path,
                edges=edges,
                length=len(edges),
            )
        except nx.NetworkXNoPath:
            return None
        except Exception:
            return None

    def get_centrality(self) -> CentralityScores:
        """中心性スコアを算出する."""
        if self._graph.number_of_nodes() == 0:
            return CentralityScores(
                pagerank={},
                degree_centrality={},
                betweenness_centrality={},
                closeness_centrality={},
            )

        pagerank = nx.pagerank(self._graph, alpha=0.85, max_iter=100, tol=1e-6)
        degree_cent = nx.degree_centrality(self._graph)

        betweenness = None
        closeness = None
        if self._graph.number_of_nodes() <= 1000:
            betweenness = nx.betweenness_centrality(self._graph, k=min(100, self._graph.number_of_nodes()))
            try:
                closeness = nx.closeness_centrality(self._graph)
            except Exception:
                pass

        return CentralityScores(
            pagerank=pagerank,
            degree_centrality=degree_cent,
            betweenness_centrality=betweenness,
            closeness_centrality=closeness,
        )

    def get_all_nodes(
        self,
        limit: int = 5000,
        labels: list[str] | None = None,
    ) -> list[GraphNode]:
        """全ノードを取得する."""
        nodes = []
        for node_id, data in self._graph.nodes(data=True):
            if labels and data.get("label") not in labels:
                continue
            nodes.append(GraphNode(
                id=node_id,
                label=data.get("label", "Entity"),
                name=data.get("name", node_id),
                properties={k: v for k, v in data.items() if k not in ("label", "name")},
            ))
            if len(nodes) >= limit:
                break
        return nodes

    def get_all_edges(
        self,
        limit: int = 10000,
    ) -> list[GraphEdge]:
        """全エッジを取得する."""
        edges = []
        for u, v, data in self._graph.edges(data=True):
            edges.append(GraphEdge(
                source=u,
                target=v,
                relation_type=data.get("relation_type", "RELATED_TO"),
                properties={k: v for k, v in data.items() if k != "relation_type"},
            ))
            if len(edges) >= limit:
                break
        return edges

    def get_stats(self) -> GraphStats:
        """グラフ統計情報を取得する."""
        labels = set()
        rel_types = set()
        for _, data in self._graph.nodes(data=True):
            if "label" in data:
                labels.add(data["label"])
        for _, _, data in self._graph.edges(data=True):
            if "relation_type" in data:
                rel_types.add(data["relation_type"])

        return GraphStats(
            node_count=self._graph.number_of_nodes(),
            edge_count=self._graph.number_of_edges(),
            labels=sorted(labels),
            relationship_types=sorted(rel_types),
        )

    def delete_node(
        self,
        label: str,
        name: str,
        detach: bool = True,
    ) -> bool:
        """ノードを削除する."""
        if name not in self._graph:
            return False
        try:
            self._graph.remove_node(name)
            return True
        except Exception:
            return False

    def delete_edge(
        self,
        source_label: str,
        source_name: str,
        target_label: str,
        target_name: str,
        relation_type: str,
    ) -> bool:
        """エッジを削除する."""
        if not self._graph.has_edge(source_name, target_name):
            return False
        try:
            rel_type_upper = relation_type.upper()
            edges_to_remove = []
            for key, data in self._graph[source_name][target_name].items():
                if data.get("relation_type", "").upper() == rel_type_upper:
                    edges_to_remove.append((source_name, target_name, key))
            for u, v, k in edges_to_remove:
                self._graph.remove_edge(u, v, k)
            return len(edges_to_remove) > 0
        except Exception:
            return False

    def clear(self) -> None:
        """グラフをクリアする."""
        self._graph.clear()

    def _init_sqlite_schema(self, conn: sqlite3.Connection) -> None:
        """SQLite スキーマを初期化する."""
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                name TEXT NOT NULL,
                properties TEXT NOT NULL DEFAULT '{}'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                properties TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY (source_id) REFERENCES graph_nodes(id),
                FOREIGN KEY (target_id) REFERENCES graph_nodes(id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_source ON graph_edges(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_target ON graph_edges(target_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_edges_relation ON graph_edges(relation_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_nodes_label ON graph_nodes(label)")
        conn.commit()

    def save_to_sqlite(self, db_path: str) -> bool:
        """グラフを SQLite に永続化する."""
        try:
            conn = sqlite3.connect(db_path)
            self._init_sqlite_schema(conn)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM graph_edges")
            cursor.execute("DELETE FROM graph_nodes")

            for node_id, data in self._graph.nodes(data=True):
                props = {k: v for k, v in data.items() if k not in ("label", "name")}
                cursor.execute(
                    "INSERT INTO graph_nodes (id, label, name, properties) VALUES (?, ?, ?, ?)",
                    (node_id, data.get("label", "Entity"), data.get("name", node_id), json.dumps(props, ensure_ascii=False)),
                )

            edge_id = 0
            for u, v, data in self._graph.edges(data=True):
                props = {k: v for k, v in data.items() if k != "relation_type"}
                cursor.execute(
                    "INSERT INTO graph_edges (source_id, target_id, relation_type, properties) VALUES (?, ?, ?, ?)",
                    (u, v, data.get("relation_type", "RELATED_TO"), json.dumps(props, ensure_ascii=False)),
                )
                edge_id += 1

            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def load_from_sqlite(self, db_path: str) -> bool:
        """SQLite からグラフを復元する."""
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            self._graph.clear()

            cursor.execute("SELECT id, label, name, properties FROM graph_nodes")
            for row in cursor.fetchall():
                props = json.loads(row["properties"]) if row["properties"] else {}
                props["label"] = row["label"]
                props["name"] = row["name"]
                self._graph.add_node(row["id"], **props)

            cursor.execute("SELECT source_id, target_id, relation_type, properties FROM graph_edges")
            for row in cursor.fetchall():
                props = json.loads(row["properties"]) if row["properties"] else {}
                props["relation_type"] = row["relation_type"]
                self._graph.add_edge(row["source_id"], row["target_id"], **props)

            conn.close()
            return True
        except Exception:
            return False

    def is_available(self) -> bool:
        """ストアが利用可能かどうかを返す."""
        return True

    def get_nx_graph(self) -> nx.MultiDiGraph:
        """内部の NetworkX グラフを取得する (上級用途)."""
        return self._graph


def create_networkx_store(sqlite_path: str | None = None) -> NetworkXGraphStore:
    """NetworkXGraphStore ファクトリ関数.

    Args:
        sqlite_path: SQLite DB パス (None の場合はインメモリのみ)

    Returns:
        NetworkXGraphStore インスタンス
    """
    return NetworkXGraphStore(sqlite_path)