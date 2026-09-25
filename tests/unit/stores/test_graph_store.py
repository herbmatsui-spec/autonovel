"""Step 11: GraphStore インターフェーステスト (モックDB使用)。"""
from __future__ import annotations

from src.stores.graph_store import GraphStore, InMemoryGraphStore


class TestGraphStore:
    """GraphStore テスト。"""

    def test_upsert_and_query(self):
        """エッジ upsert・最新取得。"""
        store: GraphStore = InMemoryGraphStore()
        store.upsert_edge("A", "B", {"tension": 0.8, "cause": "betrayal", "episode": 14})
        store.upsert_edge("A", "B", {"tension": 0.4, "cause": "rescue", "episode": 15})

        latest = store.get_latest_edge("A", "B")
        assert latest is not None
        assert latest["tension"] == 0.4
        assert latest["cause"] == "rescue"
        assert latest["episode"] == 15
        assert "timestamp" in latest

    def test_get_latest_edge_missing(self):
        """存在しないペアは None。"""
        store: GraphStore = InMemoryGraphStore()
        assert store.get_latest_edge("X", "Y") is None

    def test_query_causal_path(self):
        """因果パス取得。"""
        store: GraphStore = InMemoryGraphStore()
        store.upsert_edge("A", "B", {"cause": "betrayal", "episode": 14})
        store.upsert_edge("B", "C", {"cause": "rescue", "episode": 15})

        path = store.query_causal_path("A", "C", max_hops=3)
        assert len(path) == 2
        assert path[0]["from"] == "A"
        assert path[0]["to"] == "B"
        assert path[0]["cause"] == "betrayal"
        assert path[1]["from"] == "B"
        assert path[1]["to"] == "C"
        assert path[1]["cause"] == "rescue"

    def test_query_causal_path_max_hops(self):
        """max_hops 制限。"""
        store: GraphStore = InMemoryGraphStore()
        store.upsert_edge("A", "B", {"cause": "e1", "episode": 1})
        store.upsert_edge("B", "C", {"cause": "e2", "episode": 2})
        store.upsert_edge("C", "D", {"cause": "e3", "episode": 3})

        # max_hops=2 では A→D に到達できない
        assert store.query_causal_path("A", "D", max_hops=2) == []
        # max_hops=3 で到達
        assert len(store.query_causal_path("A", "D", max_hops=3)) == 3

    def test_query_causal_path_no_path(self):
        """パスが存在しない場合。"""
        store: GraphStore = InMemoryGraphStore()
        store.upsert_edge("A", "B", {"cause": "e1", "episode": 1})
        assert store.query_causal_path("A", "Z", max_hops=3) == []

    def test_interface_conformance(self):
        """InMemoryGraphStore は GraphStore を実装する。"""
        assert issubclass(InMemoryGraphStore, GraphStore)
