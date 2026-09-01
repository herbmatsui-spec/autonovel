"""
kernels/graph.py - 物語状態グラフ管理
"""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NarrativeState(str, Enum):
    """物語の状態"""

    SETUP = "setup"  # 冒頭・導入
    INCITING = "inciting"  # 発端事件
    RISING = "rising"  # 展開
    CLIMAX = "climax"  # クライマックス
    FALLING = "falling"  # 降下
    RESOLUTION = "resolution"  # 解決・結末


@dataclass
class NarrativeNode:
    """物語グラフのノード"""

    node_id: str
    state: NarrativeState
    title: str
    description: str
    chapter_number: int
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.state, str):
            self.state = NarrativeState(self.state)


@dataclass
class NarrativeEdge:
    """物語グラフのエッジ"""

    from_node: str
    to_node: str
    edge_type: str = "sequential"  # sequential, parallel, flashback, flashforward
    weight: float = 1.0
    condition: str | None = None


class NarrativeStateGraph:
    """
    物語の状態遷移を管理するグラフ
    """

    def __init__(self):
        self.nodes: dict[str, NarrativeNode] = {}
        self.edges: list[NarrativeEdge] = []
        self._current_state = NarrativeState.SETUP
        self._lock = asyncio.Lock()

    def add_node(self, node: NarrativeNode) -> None:
        """ノードを追加"""
        self.nodes[node.node_id] = node

    def add_edge(self, edge: NarrativeEdge) -> None:
        """エッジを追加"""
        self.edges.append(edge)

    def get_node(self, node_id: str) -> NarrativeNode | None:
        """ノードを取得"""
        return self.nodes.get(node_id)

    def get_adjacent_nodes(self, node_id: str) -> list[NarrativeNode]:
        """隣接ノードを取得"""
        adjacent = []
        for edge in self.edges:
            if edge.from_node == node_id:
                target = self.nodes.get(edge.to_node)
                if target:
                    adjacent.append(target)
        return adjacent

    def get_path(self, from_node: str, to_node: str) -> list[str]:
        """2ノード間のパスを取得（BFS）"""
        from collections import deque

        visited = set()
        queue = deque([(from_node, [from_node])])

        while queue:
            current, path = queue.popleft()
            if current == to_node:
                return path

            if current in visited:
                continue
            visited.add(current)

            for edge in self.edges:
                if edge.from_node == current and edge.to_node not in visited:
                    queue.append((edge.to_node, path + [edge.to_node]))

        return []

    def validate_transition(self, from_state: NarrativeState, to_state: NarrativeState) -> bool:
        """状態遷移が有効か検証"""
        # 基本的な順序検証
        order = [
            NarrativeState.SETUP,
            NarrativeState.INCITING,
            NarrativeState.RISING,
            NarrativeState.CLIMAX,
            NarrativeState.FALLING,
            NarrativeState.RESOLUTION,
        ]

        try:
            from_idx = order.index(from_state)
            to_idx = order.index(to_state)
            return to_idx >= from_idx
        except ValueError:
            return False

    @property
    def current_state(self) -> NarrativeState:
        return self._current_state

    def set_current_state(self, state: NarrativeState) -> None:
        if self.validate_transition(self._current_state, state):
            self._current_state = state


class NarrativeStateManager:
    """
    物語状態の管理クラス
    """

    def __init__(self):
        self.graph = NarrativeStateGraph()
        self.active_chapter = 0

    async def initialize_story(self, outline: list[dict[str, Any]]) -> None:
        """物語のアウトラインから初期化"""
        for i, chapter_data in enumerate(outline):
            node = NarrativeNode(
                node_id=f"ch{i + 1}",
                state=chapter_data.get("state", NarrativeState.RISING),
                title=chapter_data.get("title", f"Chapter {i + 1}"),
                description=chapter_data.get("description", ""),
                chapter_number=i + 1,
                dependencies=chapter_data.get("dependencies", []),
                metadata=chapter_data.get("metadata", {}),
            )
            self.graph.add_node(node)

            # 連続する章を接続
            if i > 0:
                self.graph.add_edge(
                    NarrativeEdge(from_node=f"ch{i}", to_node=f"ch{i + 1}", edge_type="sequential")
                )

    def get_chapter_state(self, chapter: int) -> NarrativeState | None:
        """章の状態を取得"""
        node = self.graph.get_node(f"ch{chapter}")
        if node:
            return node.state
        return None

    def advance_chapter(self) -> bool:
        """次の章へ進める"""
        next_chapter = self.active_chapter + 1
        node = self.graph.get_node(f"ch{next_chapter}")
        if node:
            self.active_chapter = next_chapter
            self.graph.set_current_state(node.state)
            return True
        return False
