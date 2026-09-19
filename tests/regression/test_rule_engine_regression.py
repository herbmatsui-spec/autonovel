"""Step 18: ベースライン生成精度テスト。

既知プロットイベント列 → 期待感情ベクトルのリグレッション検証。
"""
from __future__ import annotations

import pytest

from src.pipeline.emotional_residue import EmotionType
from src.rules.engine import RuleEngine
from src.rules.emotional_rules import EmotionalRule, PlotContext
from src.rules.plot_events import PlotEvent, PlotEventType, Role
from src.rules.rule_loader import DEFAULT_RULES_PATH, RuleLoader
from src.rules.state_machine import EmotionalStateMachine


@pytest.fixture
def engine():
    """デフォルトルールセットでエンジンを生成。"""
    rules = RuleLoader().load_rules(DEFAULT_RULES_PATH)
    return RuleEngine(rules=rules, state_machine=EmotionalStateMachine())


class TestRuleEngineRegression:
    """ベースライン生成精度リグレッション。"""

    def test_betrayal_then_rescue(self, engine):
        """裏切り→救出で恐怖減衰・信頼回復。"""
        events = [
            PlotEvent("e1_betrayal", 1, 1, PlotEventType.BETRAYAL,
                      roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"}),
            PlotEvent("e2_rescue", 2, 1, PlotEventType.RESCUE,
                      roles={Role.VICTIM: "A", Role.RESCUER: "B"}),
        ]
        snapshot = None
        prev_ep = None
        for ep in (1, 2):
            engine.process_episode(ep, [events[ep - 1]],
                                   previous_snapshot=snapshot, previous_episode=prev_ep)
            snapshot = engine.last_snapshot
            prev_ep = ep

        final = engine.last_vector
        # 裏切り直後の恐怖 0.5 → 2話経過で減衰 (0.5 * 0.9 = 0.45)
        fear = final.get_value("A", "B", EmotionType.FEAR)
        assert fear == pytest.approx(0.45)
        assert fear < 0.5  # 減衰

        # 信頼: -0.7 → 減衰 -0.63 → rescue +0.5 = -0.13
        trust = final.get_value("A", "B", EmotionType.TRUST)
        assert trust == pytest.approx(-0.13)
        assert trust > -0.7  # 回復傾向

    def test_forced_coop_high_tension(self, engine):
        """高緊張下の強制協力で緊張微増・理解増 (trust +0.2)。"""
        # 事前に緊張を高める
        engine.state_machine.apply_delta("A", "B", EmotionType.TENSION, 0.7,
                                         decay_per_episode=0.12)
        snapshot = engine.state_machine.snapshot()

        # 高緊張下 (0.7 >= 0.6) で強制協力
        event = PlotEvent("e1_coop", 5, 1, PlotEventType.FORCED_COOPERATION,
                          roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"},
                          metadata={"previous_tension": 0.7})
        vector = engine.process_episode(5, [event], previous_snapshot=snapshot,
                                        previous_episode=4)

        # 緊張微増: 0.7 * (1-0.1) (restore 時はデフォルト decay 0.1) + 0.3 = 0.93
        tension = vector.get_value("A", "B", EmotionType.TENSION)
        assert tension == pytest.approx(0.7 * 0.9 + 0.3)
        assert tension > 0.7  # 微増

        # trust: 0 + 0.2 (理解/信頼の構築)
        trust = vector.get_value("A", "B", EmotionType.TRUST)
        assert trust == pytest.approx(0.2)
        assert trust > 0.0

    def test_decay_over_5_episodes(self, engine):
        """5話放置で値が半減以下に (decay_per_episode=0.15)。"""
        engine.state_machine.apply_delta("A", "B", EmotionType.AFFECTION, -0.6,
                                         decay_per_episode=0.15)
        initial_value = -0.6

        engine.apply_inter_episode_decay(5)
        final_value = engine.state_machine.get_value("A", "B", EmotionType.AFFECTION)
        # -0.6 * 0.85^5 = -0.2662
        assert final_value == pytest.approx(-0.6 * 0.85**5)
        # 半減以下 (絶対値が初期値の半分以下)
        assert abs(final_value) <= abs(initial_value) / 2

    def test_low_tension_forced_coop_skipped(self, engine):
        """低緊張下の強制協力は適用されない (条件フィルタ)。"""
        event = PlotEvent("e1_coop", 1, 1, PlotEventType.FORCED_COOPERATION,
                          roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"},
                          metadata={"previous_tension": 0.3})
        vector = engine.process_episode(1, [event])
        # tension_above 0.6 条件を満たさないため trust に変化なし
        assert vector.get_value("A", "B", EmotionType.TRUST) == 0.0

    def test_confession_increases_intimacy(self, engine):
        """告白で親密度が上昇。"""
        event = PlotEvent("e1_confession", 1, 1, PlotEventType.CONFESSION,
                          roles={Role.CONFESSOR: "A", Role.LISTENER: "B"})
        vector = engine.process_episode(1, [event])
        assert vector.get_value("A", "B", EmotionType.INTIMACY) == pytest.approx(0.6)
        assert vector.get_value("A", "B", EmotionType.AFFECTION) == pytest.approx(0.5)
