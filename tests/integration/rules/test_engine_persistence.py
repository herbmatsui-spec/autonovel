"""Step 13: エンジン統合・永続化フックテスト。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.pipeline.emotional_residue import EmotionType
from src.rules.engine import RULE_ENGINE_NAMESPACE, RuleEngine
from src.rules.emotional_rules import PlotContext
from src.rules.plot_events import PlotEvent, PlotEventType, Role
from src.rules.rule_loader import DEFAULT_RULES_PATH, RuleLoader
from src.rules.state_machine import EmotionalStateMachine
from src.stores.event_log import EventLogStore
from src.stores.graph_store import InMemoryGraphStore


class MockVectorStore:
    """テスト用インメモリ VectorStore。"""

    def __init__(self):
        self.saved: dict[tuple[str, str], object] = {}

    def upsert(self, namespace: str, key: str, vector) -> None:
        self.saved[(namespace, key)] = vector


class NullStore:
    """永続化しないストア (None と同じ挙動)。"""


def _make_engine():
    rules = RuleLoader().load_rules(DEFAULT_RULES_PATH)
    return RuleEngine(rules=rules, state_machine=EmotionalStateMachine())


class TestEnginePersistence:
    """persist_results テスト。"""

    def test_persist_to_all_stores(self):
        """Vector/Graph/Log の 3 ストアに正しく書き込まれる。"""
        tmpdir = Path(tempfile.mkdtemp())
        engine = _make_engine()
        event = PlotEvent(
            "ep14_betrayal", 14, 1, PlotEventType.BETRAYAL,
            roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"},
        )
        engine.process_episode(14, [event], initial_context=PlotContext(episode=14))

        vector_store = MockVectorStore()
        graph_store = InMemoryGraphStore()
        log_store = EventLogStore(str(tmpdir / "emotional_events.jsonl"))

        engine.persist_results(vector_store, graph_store, log_store, episode=14)

        # Vector: rule_engine ネームスペース
        assert (RULE_ENGINE_NAMESPACE, "rule_engine:ep14") in vector_store.saved
        vec = vector_store.saved[(RULE_ENGINE_NAMESPACE, "rule_engine:ep14")]
        assert vec.get_value("A", "B", EmotionType.TENSION) == pytest.approx(0.8)

        # Graph: エッジ upsert 済み
        edge = graph_store.get_latest_edge("A", "B")
        assert edge is not None
        assert edge["episode"] == 14
        assert edge["cause"] == "betrayal"
        # 全感情プロパティが記録されている
        for prop in ("affection", "tension", "fear", "trust", "intimacy"):
            assert prop in edge

        # Log: 全シグナル append 済み
        signals = log_store.query(pair=("A", "B"))
        assert len(signals) == 4

    def test_persist_with_null_stores(self):
        """None ストアを渡してもエラーにならない。"""
        engine = _make_engine()
        event = PlotEvent(
            "ep14_betrayal", 14, 1, PlotEventType.BETRAYAL,
            roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"},
        )
        engine.process_episode(14, [event])
        # None を渡す → 何もしない (エラーなし)
        engine.persist_results(None, None, None, episode=14)

    def test_persist_multiple_episodes(self):
        """複数エピソードの永続化。"""
        tmpdir = Path(tempfile.mkdtemp())
        engine = _make_engine()
        vector_store = MockVectorStore()
        graph_store = InMemoryGraphStore()
        log_store = EventLogStore(str(tmpdir / "emotional_events.jsonl"))

        snapshot = None
        prev_ep = None
        for ep in (14, 15):
            if ep == 14:
                event = PlotEvent(f"ep{ep}_betrayal", ep, 1, PlotEventType.BETRAYAL,
                                  roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"})
            else:
                event = PlotEvent(f"ep{ep}_rescue", ep, 1, PlotEventType.RESCUE,
                                  roles={Role.VICTIM: "A", Role.RESCUER: "B"})
            engine.process_episode(ep, [event], previous_snapshot=snapshot, previous_episode=prev_ep)
            engine.persist_results(vector_store, graph_store, log_store, episode=ep)
            snapshot = engine.last_snapshot
            prev_ep = ep

        # 各エピソードが永続化されている
        assert (RULE_ENGINE_NAMESPACE, "rule_engine:ep14") in vector_store.saved
        assert (RULE_ENGINE_NAMESPACE, "rule_engine:ep15") in vector_store.saved

        # Graph にはエッジ履歴 (persist はベクトル内の全感情を upsert するため
        # 1 エピソードあたり複数エッジが蓄積される)
        edges = graph_store.get_all_edges()
        assert ("A", "B") in edges
        episodes_in_edges = {e["episode"] for e in edges[("A", "B")]}
        assert episodes_in_edges == {14, 15}
        # ep14 のエッジの cause は betrayal
        ep14_edges = [e for e in edges[("A", "B")] if e["episode"] == 14]
        assert all(e["cause"] == "betrayal" for e in ep14_edges)
        # ep15 のエッジには rescue 由来も含まれる
        ep15_edges = [e for e in edges[("A", "B")] if e["episode"] == 15]
        causes_ep15 = {e["cause"] for e in ep15_edges}
        assert "rescue" in causes_ep15
