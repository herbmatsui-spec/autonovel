"""グラフ知識ストアの抽象インターフェース.

Apache AGE (PostgreSQL) と NetworkX (Pure Python/SQLite) の共通操作を定義する。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class GraphNode:
    """グラフノードの表現."""
    id: str
    label: str
    name: str
    properties: dict[str, Any]


@dataclass
class GraphEdge:
    """グラフエッジの表現."""
    source: str
    target: str
    relation_type: str
    properties: dict[str, Any]


@dataclass
class GraphStats:
    """グラフ統計情報."""
    node_count: int
    edge_count: int
    labels: list[str]
    relationship_types: list[str]


@dataclass
class CentralityScores:
    """中心性スコア."""
    pagerank: dict[str, float]
    degree_centrality: dict[str, float]
    betweenness_centrality: dict[str, float] | None = None
    closeness_centrality: dict[str, float] | None = None


@dataclass
class NeighborResult:
    """近傍探索結果."""
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    depth: int


@dataclass
class PathResult:
    """パス探索結果."""
    nodes: list[str]
    edges: list[tuple[str, str, str]]  # (source, relation_type, target)
    length: int


class GraphKnowledgeStore(ABC):
    """グラフ知識ストアの抽象基底クラス.

    Apache AGE (PostgreSQL) と NetworkX (Pure Python/SQLite) の
    共通インターフェースを提供する。
    """

    @abstractmethod
    def add_entity(
        self,
        label: str,
        name: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """エンティティ (ノード) を追加または更新する.

        Args:
            label: ノードラベル (例: Character, Location, Item)
            name: ノード名 (ユニークキー)
            properties: 追加プロパティ

        Returns:
            成功した場合 True
        """
        ...

    @abstractmethod
    def add_relation(
        self,
        source_label: str,
        source_name: str,
        target_label: str,
        target_name: str,
        relation_type: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """リレーション (エッジ) を追加または更新する.

        Args:
            source_label: 始点ノードラベル
            source_name: 始点ノード名
            target_label: 終点ノードラベル
            target_name: 終点ノード名
            relation_type: 関係タイプ (例: FRIEND, LOCATED_IN, POSSESSES)
            properties: 関係プロパティ

        Returns:
            成功した場合 True
        """
        ...

    @abstractmethod
    def find_neighbors(
        self,
        entity_id: str,
        hops: int = 2,
        relationship_types: list[str] | None = None,
        direction: str = "both",
        limit: int = 50,
    ) -> NeighborResult:
        """指定エンティティから N ホップ以内の近傍を探索する.

        Args:
            entity_id: 起点エンティティ名
            hops: 最大ホップ数 (デフォルト: 2)
            relationship_types: フィルタする関係タイプ
            direction: "outgoing" | "incoming" | "both"
            limit: 最大取得件数

        Returns:
            NeighborResult: ノード・エッジリストと深度
        """
        ...

    @abstractmethod
    def find_shortest_path(
        self,
        source_name: str,
        target_name: str,
        max_depth: int = 5,
    ) -> PathResult | None:
        """2ノード間の最短パスを探索する.

        Args:
            source_name: 始点ノード名
            target_name: 終点ノード名
            max_depth: 最大探索深度

        Returns:
            PathResult または None (パスが見つからない場合)
        """
        ...

    @abstractmethod
    def get_centrality(self) -> CentralityScores:
        """中心性スコアを算出する.

        Returns:
            CentralityScores: PageRank、次数中心性など
        """
        ...

    @abstractmethod
    def get_all_nodes(
        self,
        limit: int = 5000,
        labels: list[str] | None = None,
    ) -> list[GraphNode]:
        """全ノードを取得する."""
        ...

    @abstractmethod
    def get_all_edges(
        self,
        limit: int = 10000,
    ) -> list[GraphEdge]:
        """全エッジを取得する."""
        ...

    @abstractmethod
    def get_stats(self) -> GraphStats:
        """グラフ統計情報を取得する."""
        ...

    @abstractmethod
    def delete_node(
        self,
        label: str,
        name: str,
        detach: bool = True,
    ) -> bool:
        """ノードを削除する."""
        ...

    @abstractmethod
    def delete_edge(
        self,
        source_label: str,
        source_name: str,
        target_label: str,
        target_name: str,
        relation_type: str,
    ) -> bool:
        """エッジを削除する."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """グラフをクリアする."""
        ...

    @abstractmethod
    def save_to_sqlite(self, db_path: str) -> bool:
        """グラフを SQLite に永続化する.

        Args:
            db_path: SQLite データベースファイルパス

        Returns:
            成功した場合 True
        """
        ...

    @abstractmethod
    def load_from_sqlite(self, db_path: str) -> bool:
        """SQLite からグラフを復元する.

        Args:
            db_path: SQLite データベースファイルパス

        Returns:
            成功した場合 True
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """ストアが利用可能かどうかを返す."""
        ...