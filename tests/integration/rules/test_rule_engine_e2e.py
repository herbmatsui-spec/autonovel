"""Step 14: ルールエンジン統合テスト。

config/plot_events.yaml (ep14-16) のサンプルで 3話分のベースライン生成を検証する。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.pipeline.emotional_residue import EmotionType
from src.rules.engine import RULE_ENGINE_NAMESPACE, RuleEngine
from src.rules.rule_loader import (
    DEFAULT_EVENTS_PATH,
    DEFAULT_RULES_PATH,
    RuleLoader,
    parse_episode_events,
)
from src.rules.state_machine import EmotionalStateMachine
from src.stores.event_log import EventLogStore
from src.stores.graph_store import InMemoryGraphStore


class MockVectorStore:
    """テスト用インメモリ VectorStore。"""

    def __init__(self):
        self.saved: dict[tuple[str, str], object] = {}

    def upsert(self, namespace: str, key: str, vector) -> None:
        self.saved[(namespace, key)] = vector

    def get(self, namespace: str, key: str):
        return self.saved.get((namespace, key))


@pytest.fixture
def stores():
    """3 ストアのフィクスチャ。"""
    tmpdir = Path(tempfile.mkdtemp())
    return {
        "vector": MockVectorStore(),
        "graph": InMemoryGraphStore(),
        "log": EventLogStore(str(tmpdir / "emotional_events.jsonl")),
    }


class TestRuleEngineE2E:
    """ルールエンジン統合テスト。"""

    def test_three_episode_baseline_generation(self, stores):
        """3話分のベースライン生成と全ストア永続化。"""
        rules = RuleLoader().load_rules(DEFAULT_RULES_PATH)
        engine = RuleEngine(rules=rules, state_machine=EmotionalStateMachine())
        events_by_ep = parse_episode_events(DEFAULT_EVENTS_PATH)

        snapshot = None
        prev_ep = None
        for ep in (14, 15, 16):
            events = events_by_ep[ep]
            engine.process_episode(
                ep, events,
                previous_snapshot=snapshot,
                previous_episode=prev_ep,
            )
            engine.persist_results(
                stores["vector"], stores["graph"], stores["log"], episode=ep,
            )
            snapshot = engine.last_snapshot
            prev_ep = ep

        # VectorStore に rule_engine:ep14, ep15, ep16 存在
        for ep in (14, 15, 16):
            key = f"rule_engine:ep{ep}"
            assert (RULE_ENGINE_NAMESPACE, key) in stores["vector"].saved, f"{key} missing"
            vec = stores["vector"].get(RULE_ENGINE_NAMESPACE, key)
            assert vec.episode_id == f"ep{ep}"

        # Graph にエッジ蓄積 (A->B ペアが 3話分)
        edges = stores["graph"].get_all_edges()
        assert ("A", "B") in edges
        assert len(edges[("A", "B")]) >= 3

        # Log に全シグナル記録
        signals = stores["log"].query(pair=("A", "B"))
        assert len(signals) > 0
        episodes_logged = {s.episode_id for s in signals}
        assert episodes_logged == {"ep14", "ep15", "ep16"}

    def test_known_pair_values_in_expected_range(self, stores):
        """既知ペアの値が期待レンジ内。"""
        rules = RuleLoader().load_rules(DEFAULT_RULES_PATH)
        engine = RuleEngine(rules=rules, state_machine=EmotionalStateMachine())
        events_by_ep = parse_episode_events(DEFAULT_EVENTS_PATH)

        snapshot = None
        prev_ep = None
        for ep in (14, 15, 16):
            engine.process_episode(
                ep, events_by_ep[ep],
                previous_snapshot=snapshot,
                previous_episode=prev_ep,
            )
            snapshot = engine.last_snapshot
            prev_ep = ep

        final = engine.last_vector
        # 全値は -1.0 ~ 1.0 内
        for (_, _, _), value in final.signals.items():
            assert -1.0 <= value <= 1.0

        # 期待フロー (ep14 betrayal → ep15 rescue → ep16 confession):
        # trust: -0.7 → decay*0.9=-0.63, rescue+0.5=-0.13 → decay*0.9=-0.117
        trust = final.get_value("A", "B", EmotionType.TRUST)
        assert trust == pytest.approx(-0.117)
        # 裏切り初期値 (-0.7) よりは回復している
        assert trust > -0.7
        # 緊張: 0.8 → decay*0.9=0.72, rescue-0.3=0.42 → decay*0.9=0.378, confession-0.2=0.178
        tension = final.get_value("A", "B", EmotionType.TENSION)
        assert tension == pytest.approx(0.178)
        # 好感度: -0.6 → decay*0.9=-0.54, rescue+0.4=-0.14 → decay*0.9=-0.126, confession+0.5=0.374
        affection = final.get_value("A", "B", EmotionType.AFFECTION)
        assert affection == pytest.approx(0.374)

    def test_decay_applied_across_boundaries(self, stores):
        """話境界で減衰が正しく適用される。"""
        rules = RuleLoader().load_rules(DEFAULT_RULES_PATH)
        engine = RuleEngine(rules=rules, state_machine=EmotionalStateMachine())
        events_by_ep = parse_episode_events(DEFAULT_EVENTS_PATH)

        # ep14 のみ
        engine.process_episode(14, events_by_ep[14])
        tension_ep14 = engine.last_vector.get_value("A", "B", EmotionType.TENSION)
        assert tension_ep14 == pytest.approx(0.8)

        # ep15 (減衰あり)
        engine.process_episode(
            15, events_by_ep[15],
            previous_snapshot=engine.last_snapshot,
            previous_episode=14,
        )
        tension_ep15 = engine.last_vector.get_value("A", "B", EmotionType.TENSION)
        # 0.8 * 0.9 = 0.72 → rescue -0.3 → 0.42
        assert tension_ep15 == pytest.approx(0.42)
        assert tension_ep15 < tension_ep14
