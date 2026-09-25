"""Step 15: パイプラインへのルールエンジンステージ追加テスト。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.pipeline.compression_pipeline import (
    NAMESPACE_RULE_ENGINE,
    CompressionPipeline,
    create_rule_engine,
)
from src.pipeline.emotional_residue import EmotionType
from src.rules.engine import RuleEngine
from src.rules.rule_loader import DEFAULT_EVENTS_PATH, DEFAULT_RULES_PATH
from src.rules.state_machine import EmotionalStateMachine
from src.stores.event_log import EventLogStore
from src.stores.graph_store import InMemoryGraphStore


class MockVectorStore:
    """テスト用インメモリ VectorStore。"""

    def __init__(self):
        self.saved: dict[tuple[str, str], object] = {}

    def upsert(self, namespace: str, key: str, vector) -> None:
        self.saved[(namespace, key)] = vector

    def get_latest(self, namespace: str, pair):
        matching = [v for (ns, k), v in self.saved.items() if ns == namespace]
        if not matching:
            return None
        return matching[-1]


class TestRuleEngineStage:
    """ルールエンジンステージテスト。"""

    def test_rule_engine_stage_runs(self):
        """パイプライン実行時にルールエンジンステージが動作する。"""
        tmpdir = Path(tempfile.mkdtemp())
        rule_engine = create_rule_engine()
        vector_store = MockVectorStore()
        graph_store = InMemoryGraphStore()
        log_store = EventLogStore(str(tmpdir / "emotional_events.jsonl"))

        pipeline = CompressionPipeline(
            vector_store=vector_store,
            rule_engine=rule_engine,
            graph_store=graph_store,
            log_store=log_store,
        )
        result = pipeline.run("ep14", "テスト脚本", episode=14)

        # ルールエンジンステージが実行された
        assert result["rule_engine_vector"] is True
        assert result["namespaces"][NAMESPACE_RULE_ENGINE] is True
        # VectorStore に rule_engine ネームスペースで保存された
        assert any(ns == NAMESPACE_RULE_ENGINE for ns, _ in vector_store.saved)

    def test_rule_engine_disabled_stage_skipped(self):
        """ルールエンジン未指定時はステージがスキップされる。"""
        pipeline = CompressionPipeline(vector_store=None, rule_engine=None)
        result = pipeline.run("ep14", "テスト脚本", episode=14)

        assert result["rule_engine_vector"] is False
        assert result["namespaces"][NAMESPACE_RULE_ENGINE] is False

    def test_state_inherited_across_episodes(self):
        """パイプライン経由でエピソード間の状態が引き継がれる。"""
        rule_engine = create_rule_engine()
        pipeline = CompressionPipeline(vector_store=None, rule_engine=rule_engine)

        pipeline.run("ep14", "脚本1", episode=14)
        tension_ep14 = rule_engine.last_vector.get_value("A", "B", EmotionType.TENSION)
        assert tension_ep14 == pytest.approx(0.8)

        pipeline.run("ep15", "脚本2", episode=15)
        tension_ep15 = rule_engine.last_vector.get_value("A", "B", EmotionType.TENSION)
        # 減衰 + rescue: 0.8*0.9 - 0.3 = 0.42
        assert tension_ep15 == pytest.approx(0.42)

    def test_persist_called_when_stores_available(self):
        """ストア利用可能時は永続化が呼ばれる。"""
        tmpdir = Path(tempfile.mkdtemp())
        log_path = tmpdir / "emotional_events.jsonl"
        rule_engine = create_rule_engine()
        graph_store = InMemoryGraphStore()
        log_store = EventLogStore(str(log_path))

        pipeline = CompressionPipeline(
            vector_store=None,
            rule_engine=rule_engine,
            graph_store=graph_store,
            log_store=log_store,
        )
        pipeline.run("ep14", "脚本", episode=14)

        # Log にシグナルが書き込まれた
        assert log_path.exists()
        assert log_store.count() == 4
        # Graph にエッジが書き込まれた
        assert graph_store.get_latest_edge("A", "B") is not None

    def test_create_rule_engine_helper(self):
        """create_rule_engine ヘルパー。"""
        engine = create_rule_engine(DEFAULT_RULES_PATH)
        assert isinstance(engine, RuleEngine)
        assert len(engine.rules) >= 8

    def test_create_rule_engine_custom_state_machine(self):
        """カスタム状態マシンの注入。"""
        sm = EmotionalStateMachine()
        sm.apply_delta("X", "Y", EmotionType.TRUST, 0.9)
        engine = create_rule_engine(DEFAULT_RULES_PATH, state_machine=sm)
        assert engine.state_machine is sm
        assert engine.state_machine.get_value("X", "Y", EmotionType.TRUST) == 0.9
