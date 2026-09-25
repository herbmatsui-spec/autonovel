"""Steps 9-10 補助: エピソード跨ぎ減衰とスナップショット復元の詳細テスト。"""
from __future__ import annotations

import pytest

from src.pipeline.emotional_residue import EmotionType
from src.rules.engine import RuleEngine
from src.rules.emotional_rules import EmotionalRule, PlotContext
from src.rules.plot_events import PlotEvent, PlotEventType, Role
from src.rules.rule_loader import DEFAULT_RULES_PATH, RuleLoader
from src.rules.state_machine import EmotionalStateMachine


class TestEpisodeTransitions:
    """エピソード跨ぎ処理テスト。"""

    def test_multi_episode_chain(self):
        """3話連鎖での状態継承。"""
        engine = RuleEngine(
            rules=RuleLoader().load_rules(DEFAULT_RULES_PATH),
            state_machine=EmotionalStateMachine(),
        )
        snapshot = None
        prev_ep = None
        vectors = {}
        for ep, (event_type, roles) in {
            14: ("betrayal", {Role.VICTIM: "A", Role.PERPETRATOR: "B"}),
            15: ("rescue", {Role.VICTIM: "A", Role.RESCUER: "B"}),
            16: ("confession", {Role.CONFESSOR: "A", Role.LISTENER: "B"}),
        }.items():
            events = [PlotEvent(f"ep{ep}_{event_type}", ep, 1, event_type, roles=roles)]
            vectors[ep] = engine.process_episode(
                ep, events, previous_snapshot=snapshot, previous_episode=prev_ep,
            )
            snapshot = engine.last_snapshot
            prev_ep = ep

        # ep14: betrayal → tension 0.8
        assert vectors[14].get_value("A", "B", EmotionType.TENSION) == pytest.approx(0.8)
        # ep15: 減衰 0.8*0.9=0.72 → rescue -0.3 → 0.42
        assert vectors[15].get_value("A", "B", EmotionType.TENSION) == pytest.approx(0.42)
        # ep16: 減衰 0.42*0.9=0.378、confession ルールは tension -0.2 → 0.178
        assert vectors[16].get_value("A", "B", EmotionType.TENSION) == pytest.approx(0.178)

    def test_decay_uses_largest_rule_decay(self):
        """減衰にはキーごとの decay_per_episode が使用される。"""
        rules = [
            EmotionalRule(
                event_type=PlotEventType.BETRAYAL,
                source_role=Role.VICTIM,
                target_role=Role.PERPETRATOR,
                emotion_deltas={EmotionType.AFFECTION: -0.5},
                decay_per_episode=0.1,
            ),
            EmotionalRule(
                event_type=PlotEventType.RESCUE,
                source_role=Role.VICTIM,
                target_role=Role.RESCUER,
                emotion_deltas={EmotionType.TRUST: 0.5},
                decay_per_episode=0.3,
            ),
        ]
        engine = RuleEngine(rules=rules, state_machine=EmotionalStateMachine())
        # betrayal 由来のキーには decay=0.1 が紐付く
        engine.state_machine.apply_delta("A", "B", EmotionType.AFFECTION, -0.6, decay_per_episode=0.1)
        engine.apply_inter_episode_decay(1)
        # decay=0.1 (キーごと) → -0.6 * 0.9 = -0.54
        assert engine.state_machine.get_value("A", "B", EmotionType.AFFECTION) == pytest.approx(-0.54)

    def test_no_decay_without_rules(self):
        """ルールがない場合は減衰なし。"""
        engine = RuleEngine(rules=[], state_machine=EmotionalStateMachine())
        engine.state_machine.apply_delta("A", "B", EmotionType.AFFECTION, -0.6)
        engine.apply_inter_episode_decay(3)
        assert engine.state_machine.get_value("A", "B", EmotionType.AFFECTION) == -0.6

    def test_condition_uses_metadata(self):
        """metadata の relationship_level が条件評価に使われる。"""
        rule = EmotionalRule(
            event_type=PlotEventType.SECRET_SHARED,
            source_role=Role.SHARER,
            target_role=Role.RECEIVER,
            emotion_deltas={EmotionType.INTIMACY: 0.5},
            condition=lambda ctx: ctx.relationship_level >= 0.5,
        )
        engine = RuleEngine(rules=[rule], state_machine=EmotionalStateMachine())
        event = PlotEvent("e1", 1, 1, "secret_shared",
                          roles={Role.SHARER: "A", Role.RECEIVER: "B"},
                          metadata={"relationship_level": 0.7})
        signals = engine.process_event(event, PlotContext(episode=1))
        assert len(signals) == 1

        # metadata が低い場合はスキップ
        event_low = PlotEvent("e2", 1, 2, "secret_shared",
                              roles={Role.SHARER: "A", Role.RECEIVER: "B"},
                              metadata={"relationship_level": 0.2})
        signals_low = engine.process_event(event_low, PlotContext(episode=1))
        assert signals_low == []
