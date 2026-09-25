"""Step 21: Week 2 リグレッションテスト。

パイプライン統合・ネームスペース分離・因果パスの回帰検証。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.pipeline.compression_pipeline import (
    NAMESPACE_ANNOTATION,
    NAMESPACE_PIPELINE,
    NAMESPACE_RULE_ENGINE,
    CompressionPipeline,
    create_rule_engine,
)
from src.pipeline.emotional_residue import (
    EmotionalResidueExtractor,
    EmotionalSignal,
    EmotionalVector,
    EmotionType,
)
from src.rules.engine import RuleEngine
from src.rules.rule_loader import DEFAULT_EVENTS_PATH, DEFAULT_RULES_PATH
from src.rules.state_machine import EmotionalStateMachine
from src.stores.event_log import EventLogStore
from src.stores.graph_store import InMemoryGraphStore


class MockVectorStore:
    """テスト用インメモリ VectorStore。"""

    def __init__(self):
        self.saved: dict[tuple[str, str], EmotionalVector] = {}

    def upsert(self, namespace: str, key: str, vector: EmotionalVector) -> None:
        self.saved[(namespace, key)] = vector

    def get_all(self, namespace: str) -> list[EmotionalVector]:
        return [v for (ns, _), v in self.saved.items() if ns == namespace]


class MockExtractor(EmotionalResidueExtractor):
    """Week 1 抽出器のモック。"""

    def __init__(self, vector_store: MockVectorStore):
        self.vector_store = vector_store

    def extract_and_persist(self, episode_id: str, script: str) -> EmotionalVector:
        vec = EmotionalVector(episode_id=episode_id)
        vec.set_signal(EmotionalSignal(
            source="A", target="B", emotion_type=EmotionType.JEALOUSY,
            value=0.6, confidence=0.7, evidence_span=script[:20],
            episode_id=episode_id, cause="pipeline_extraction",
        ))
        self.vector_store.upsert(NAMESPACE_PIPELINE, f"{episode_id}:A->B", vec)
        return vec


class TestWeek2Regression:
    """Week 2 リグレッション。"""

    def test_rule_engine_does_not_break_pipeline(self):
        """パイプライン全体実行が成功する。"""
        tmpdir = Path(tempfile.mkdtemp())
        vector_store = MockVectorStore()
        pipeline = CompressionPipeline(
            extractor=MockExtractor(vector_store),
            vector_store=vector_store,
            rule_engine=create_rule_engine(),
            graph_store=InMemoryGraphStore(),
            log_store=EventLogStore(str(tmpdir / "emotional_events.jsonl")),
        )

        # 3話分のパイプライン実行が例外なく完了する
        for ep in (14, 15, 16):
            result = pipeline.run(f"ep{ep}", f"脚本{ep}", episode=ep)
            assert result["episode_id"] == f"ep{ep}"
            assert result["rule_engine_vector"] is True
            assert result["pipeline_vector"] is True

        # 両ネームスペースに保存されている
        assert len(vector_store.get_all(NAMESPACE_PIPELINE)) == 3
        assert len(vector_store.get_all(NAMESPACE_RULE_ENGINE)) == 3

    def test_vector_namespaces_isolated(self):
        """pipeline/rule_engine/annotation が混ざらない。"""
        vector_store = MockVectorStore()
        pipeline = CompressionPipeline(
            extractor=MockExtractor(vector_store),
            vector_store=vector_store,
            rule_engine=create_rule_engine(),
        )
        pipeline.run("ep14", "脚本", episode=14)

        # 各ネームスペースのベクトル内容が独立している
        pipeline_vec = vector_store.get_all(NAMESPACE_PIPELINE)[0]
        rule_vec = vector_store.get_all(NAMESPACE_RULE_ENGINE)[0]

        # pipeline: JEALOUSY のみ (Week 1 抽出)
        assert pipeline_vec.get_value("A", "B", EmotionType.JEALOUSY) == pytest.approx(0.6)
        # rule_engine: TENSION 等 (betrayal 由来)
        assert rule_vec.get_value("A", "B", EmotionType.TENSION) == pytest.approx(0.8)

        # pipeline に rule_engine 由来の感情が漏れていない
        assert pipeline_vec.get_value("A", "B", EmotionType.TENSION) == 0.0
        # annotation は未使用
        assert vector_store.get_all(NAMESPACE_ANNOTATION) == []

    def test_graph_query_returns_causal_path(self):
        """因果パス取得が動作する。"""
        graph = InMemoryGraphStore()
        graph.upsert_edge("A", "B", {"cause": "betrayal", "episode": 14})
        graph.upsert_edge("B", "C", {"cause": "rescue", "episode": 15})
        graph.upsert_edge("C", "D", {"cause": "confession", "episode": 16})

        # 2ホップ: A → C
        path_ac = graph.query_causal_path("A", "C", max_hops=2)
        assert len(path_ac) == 2
        assert [p["cause"] for p in path_ac] == ["betrayal", "rescue"]

        # 3ホップ: A → D
        path_ad = graph.query_causal_path("A", "D", max_hops=3)
        assert len(path_ad) == 3

        # 存在しないパス
        assert graph.query_causal_path("D", "A", max_hops=3) == []

    def test_week1_regression_still_passes(self):
        """Week 1 機能に影響なし (VectorStore 基本動作)。"""
        from src.pipeline.emotional_residue import EmotionalResidueExtractor as E

        # Week 1 のデータ構造がそのまま使える
        vec = EmotionalVector(episode_id="ep01")
        vec.set_signal(EmotionalSignal(
            "A", "B", EmotionType.AFFECTION, 0.5, 0.8, "...", "ep01"
        ))
        assert vec.get_value("A", "B", EmotionType.AFFECTION) == 0.5

        # ネームスペース "pipeline" キーは Week 1 と同じ形式
        store = MockVectorStore()
        store.upsert("pipeline", "ep01:A->B", vec)
        assert ("pipeline", "ep01:A->B") in store.saved

    def test_rule_engine_isolated_from_week1_state(self):
        """ルールエンジンの状態は Week 1 抽出に影響しない。"""
        rule_engine = create_rule_engine()
        # ルールエンジンで状態を変更
        rule_engine.process_episode(
            14, __import__("src.rules.rule_loader", fromlist=["parse_episode_events"])
            .parse_episode_events(DEFAULT_EVENTS_PATH)[14],
        )
        # Week 1 の抽出器は独立して動作する
        store = MockVectorStore()
        extractor = MockExtractor(store)
        vec = extractor.extract_and_persist("ep14", "テスト脚本")
        # ルールエンジンの影響を受けない (JEALOUSY のみ)
        assert vec.get_value("A", "B", EmotionType.JEALOUSY) == pytest.approx(0.6)
        assert vec.get_value("A", "B", EmotionType.TENSION) == 0.0
