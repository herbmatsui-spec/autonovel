"""Step 2: 感情変化ルール定義テスト。"""
from __future__ import annotations

from src.pipeline.emotional_residue import EmotionType
from src.rules.emotional_rules import EmotionalRule, PlotContext
from src.rules.plot_events import PlotEvent, PlotEventType, Role


class TestRuleCreation:
    """EmotionalRule 生成テスト。"""

    def test_rule_creation(self):
        """基本的なルール生成。"""
        rule = EmotionalRule(
            event_type=PlotEventType.BETRAYAL,
            source_role=Role.VICTIM,
            target_role=Role.PERPETRATOR,
            emotion_deltas={
                EmotionType.AFFECTION: -0.6,
                EmotionType.TENSION: 0.8,
            },
            decay_per_episode=0.1,
        )
        assert rule.event_type == PlotEventType.BETRAYAL
        assert rule.source_role == Role.VICTIM
        assert rule.target_role == Role.PERPETRATOR
        assert rule.emotion_deltas[EmotionType.AFFECTION] == -0.6
        assert rule.decay_per_episode == 0.1

    def test_default_condition_always_true(self):
        """デフォルト条件は常に真。"""
        rule = EmotionalRule(
            event_type=PlotEventType.BETRAYAL,
            source_role=Role.VICTIM,
            target_role=Role.PERPETRATOR,
            emotion_deltas={EmotionType.AFFECTION: -0.5},
        )
        ctx = PlotContext(episode=1)
        assert rule.evaluate(ctx) is True

    def test_string_keys_normalized(self):
        """文字列キーが EmotionType に正規化される。"""
        rule = EmotionalRule(
            event_type="betrayal",
            source_role="victim",
            target_role="perpetrator",
            emotion_deltas={"affection": -0.6, "tension": 0.8},
        )
        assert rule.event_type == PlotEventType.BETRAYAL
        assert EmotionType.AFFECTION in rule.emotion_deltas
        assert EmotionType.TENSION in rule.emotion_deltas

    def test_custom_condition_evaluated(self):
        """カスタム条件が評価される。"""
        rule = EmotionalRule(
            event_type=PlotEventType.BETRAYAL,
            source_role=Role.VICTIM,
            target_role=Role.PERPETRATOR,
            emotion_deltas={EmotionType.AFFECTION: -0.5},
            condition=lambda ctx: ctx.relationship_level > 0.5,
        )
        high = PlotContext(episode=1, relationship_level=0.8)
        low = PlotContext(episode=1, relationship_level=0.2)
        assert rule.evaluate(high) is True
        assert rule.evaluate(low) is False

    def test_condition_exception_returns_false(self):
        """条件関数の例外は False 扱い。"""
        def bad_condition(ctx):
            raise RuntimeError("boom")

        rule = EmotionalRule(
            event_type=PlotEventType.BETRAYAL,
            source_role=Role.VICTIM,
            target_role=Role.PERPETRATOR,
            emotion_deltas={EmotionType.AFFECTION: -0.5},
            condition=bad_condition,
        )
        assert rule.evaluate(PlotContext(episode=1)) is False

    def test_matches(self):
        """イベントタイプ一致判定。"""
        rule = EmotionalRule(
            event_type=PlotEventType.RESCUE,
            source_role=Role.VICTIM,
            target_role=Role.RESCUER,
            emotion_deltas={EmotionType.TRUST: 0.5},
        )
        rescue_event = PlotEvent("e1", 1, 1, "rescue")
        betrayal_event = PlotEvent("e2", 1, 1, "betrayal")
        assert rule.matches(rescue_event) is True
        assert rule.matches(betrayal_event) is False
