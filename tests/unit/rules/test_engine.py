"""Steps 8-10: ルールエンジンコアテスト。"""
from __future__ import annotations

import pytest

from src.pipeline.emotional_residue import EmotionalVector, EmotionType
from src.rules.engine import RULE_ENGINE_NAMESPACE, RuleEngine
from src.rules.emotional_rules import EmotionalRule, PlotContext
from src.rules.plot_events import PlotEvent, PlotEventType, Role
from src.rules.rule_loader import RuleLoader
from src.rules.state_machine import EmotionalStateMachine

DEFAULT_RULES_PATH = RuleLoader.__module__ and __import__(
    "src.rules.rule_loader", fromlist=["DEFAULT_RULES_PATH"]
).DEFAULT_RULES_PATH


def _make_engine() -> RuleEngine:
    """デフォルトルールセットでエンジンを生成。"""
    rules = RuleLoader().load_rules(DEFAULT_RULES_PATH)
    return RuleEngine(rules=rules, state_machine=EmotionalStateMachine())


class TestProcessEvent:
    """単一イベント処理テスト。"""

    def test_process_betrayal_event(self):
        """裏切りイベント処理。"""
        engine = _make_engine()
        event = PlotEvent(
            event_id="ep14_betrayal",
            episode=14,
            scene=3,
            event_type=PlotEventType.BETRAYAL,
            roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"},
        )
        ctx = PlotContext(episode=14, relationship_level=0.6)
        signals = engine.process_event(event, ctx)

        assert len(signals) == 4  # affection, tension, fear, trust
        by_emotion = {s.emotion_type: s for s in signals}
        assert by_emotion[EmotionType.AFFECTION].source == "A"
        assert by_emotion[EmotionType.AFFECTION].target == "B"
        assert by_emotion[EmotionType.AFFECTION].value == -0.6
        assert by_emotion[EmotionType.TENSION].value == 0.8
        assert by_emotion[EmotionType.FEAR].value == 0.5
        assert by_emotion[EmotionType.TRUST].value == -0.7
        # evidence_span に event_id 記録
        for s in signals:
            assert s.evidence_span == "ep14_betrayal"
            assert s.cause == "betrayal"

    def test_condition_filters_event(self):
        """条件を満たさないイベントはスキップ。"""
        # tension_above 0.9 の条件付き betrayal ルール
        rule = EmotionalRule(
            event_type=PlotEventType.FORCED_COOPERATION,
            source_role=Role.VICTIM,
            target_role=Role.PERPETRATOR,
            emotion_deltas={EmotionType.TENSION: 0.3},
            condition=lambda ctx: ctx.previous_tension >= 0.9,
        )
        engine = RuleEngine(rules=[rule], state_machine=EmotionalStateMachine())
        event = PlotEvent("e1", 1, 1, "forced_cooperation",
                          roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"})

        # 緊張が低い → 適用されない
        low_ctx = PlotContext(episode=1, previous_tension=0.3)
        assert engine.process_event(event, low_ctx) == []

        # 緊張が高い → 適用される
        high_ctx = PlotContext(episode=1, previous_tension=0.95)
        signals = engine.process_event(event, high_ctx)
        assert len(signals) == 1

    def test_missing_role_skips(self):
        """役割に対応するキャラクターが欠落している場合はスキップ。"""
        engine = _make_engine()
        event = PlotEvent(
            "e1", 1, 1, "betrayal",
            roles={Role.VICTIM: "A"},  # perpetrator 欠落
        )
        signals = engine.process_event(event, PlotContext(episode=1))
        assert signals == []

    def test_same_source_target_skips(self):
        """source == target はスキップ。"""
        engine = _make_engine()
        event = PlotEvent(
            "e1", 1, 1, "betrayal",
            roles={Role.VICTIM: "A", Role.PERPETRATOR: "A"},
        )
        signals = engine.process_event(event, PlotContext(episode=1))
        assert signals == []


class TestProcessEpisode:
    """エピソード一括処理テスト。"""

    def test_process_full_episode(self):
        """エピソード全体の処理とベクトル変換。"""
        engine = _make_engine()
        events = [
            PlotEvent("ep14_betrayal", 14, 3, "betrayal",
                      roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"}),
            PlotEvent("ep14_secret", 14, 1, "secret_shared",
                      roles={Role.SHARER: "A", Role.RECEIVER: "B"}),
        ]
        vector = engine.process_episode(14, events)

        assert isinstance(vector, EmotionalVector)
        assert vector.episode_id == "ep14"
        # secret_shared (scene 1) が先に適用される
        # secret_shared は intimacy/trust のみ変更 (affection は不変)
        assert vector.get_value("A", "B", EmotionType.INTIMACY) == pytest.approx(0.5)
        # trust: secret で +0.4 → betrayal で -0.7 → -0.3
        assert vector.get_value("A", "B", EmotionType.TRUST) == pytest.approx(-0.3)
        # affection: betrayal のみ → -0.6
        affection = vector.get_value("A", "B", EmotionType.AFFECTION)
        assert affection == pytest.approx(-0.6)
        # スナップショットが保存されている
        assert engine.last_snapshot is not None

    def test_state_restored_from_snapshot(self):
        """前回スナップショットからの状態復元。"""
        engine = _make_engine()
        events_14 = [PlotEvent("ep14_betrayal", 14, 1, "betrayal",
                               roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"})]
        engine.process_episode(14, events_14)
        snapshot_14 = engine.last_snapshot

        events_15 = [PlotEvent("ep15_rescue", 15, 1, "rescue",
                               roles={Role.VICTIM: "A", Role.RESCUER: "B"})]
        vector_15 = engine.process_episode(
            15, events_15,
            previous_snapshot=snapshot_14,
            previous_episode=14,
        )
        # ep14 の betrayal 値 (tension 0.8) が減衰後も反映されている
        tension = vector_15.get_value("A", "B", EmotionType.TENSION)
        # 1話経過で decay=0.1 → 0.8 * 0.9 = 0.72、その後 rescue で -0.3
        assert tension == pytest.approx(0.42)
        # affection: ep14 -0.6 が減衰 → -0.6 * 0.9 = -0.54、rescue で +0.4
        assert vector_15.get_value("A", "B", EmotionType.AFFECTION) == pytest.approx(-0.14)


class TestDecay:
    """減衰処理テスト。"""

    def test_decay_across_episodes(self):
        """エピソード間減衰の動作確認。"""
        engine = _make_engine()
        sm = engine.state_machine
        sm.apply_delta("A", "B", EmotionType.AFFECTION, -0.6, decay_per_episode=0.1)

        engine.apply_inter_episode_decay(1)
        # decay=0.1 (キーごと) → -0.6 * 0.9 = -0.54
        assert sm.get_value("A", "B", EmotionType.AFFECTION) == pytest.approx(-0.54)

        engine.apply_inter_episode_decay(2)
        # -0.54 * 0.9^2 = -0.4374
        assert sm.get_value("A", "B", EmotionType.AFFECTION) == pytest.approx(-0.4374)

    def test_decay_zero_episodes_noop(self):
        """0話経過では減衰なし。"""
        engine = _make_engine()
        sm = engine.state_machine
        sm.apply_delta("A", "B", EmotionType.AFFECTION, -0.6)
        engine.apply_inter_episode_decay(0)
        assert sm.get_value("A", "B", EmotionType.AFFECTION) == -0.6


class TestPersistence:
    """永続化フックテスト。"""

    def test_persist_requires_process_episode(self):
        """process_episode 未実行時はエラー。"""
        engine = _make_engine()
        with pytest.raises(RuntimeError):
            engine.persist_results(None, None, None, episode=14)

    def test_persist_to_all_stores(self):
        """Vector/Graph/Log への書き込み。"""
        from src.stores.event_log import EventLogStore
        from src.stores.graph_store import InMemoryGraphStore

        class MockVectorStore:
            def __init__(self):
                self.saved = {}

            def upsert(self, namespace, key, vector):
                self.saved[(namespace, key)] = vector

        engine = _make_engine()
        events = [PlotEvent("ep14_betrayal", 14, 1, "betrayal",
                            roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"})]
        engine.process_episode(14, events)

        vector_store = MockVectorStore()
        graph_store = InMemoryGraphStore()
        log_store = EventLogStore(str(__import__("pathlib").Path(
            __import__("tempfile").mkdtemp()) / "test_events.jsonl"))

        engine.persist_results(vector_store, graph_store, log_store, episode=14)

        # Vector
        assert (RULE_ENGINE_NAMESPACE, "rule_engine:ep14") in vector_store.saved
        vec = vector_store.saved[(RULE_ENGINE_NAMESPACE, "rule_engine:ep14")]
        assert vec.get_value("A", "B", EmotionType.TENSION) == 0.8

        # Graph
        edge = graph_store.get_latest_edge("A", "B")
        assert edge is not None
        assert edge["tension"] == 0.8
        assert edge["cause"] == "betrayal"
        assert edge["episode"] == 14

        # Log
        from src.pipeline.emotional_residue import EmotionalSignal
        signals = log_store.query(pair=("A", "B"))
        assert len(signals) == 4
        assert all(isinstance(s, EmotionalSignal) for s in signals)
