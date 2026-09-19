"""Step 7: 感情状態マシンテスト。"""
from __future__ import annotations

import pytest

from src.pipeline.emotional_residue import EmotionType
from src.rules.state_machine import EmotionalStateMachine, MAX_VALUE, MIN_VALUE


class TestEmotionalStateMachine:
    """EmotionalStateMachine テスト。"""

    def test_apply_delta_and_clamp(self):
        """クランプ付き加算。"""
        sm = EmotionalStateMachine()

        # 通常の加算
        value = sm.apply_delta("A", "B", EmotionType.AFFECTION, 0.5)
        assert value == 0.5

        # 累積
        value = sm.apply_delta("A", "B", EmotionType.AFFECTION, 0.3)
        assert value == 0.8

        # 上限クランプ (1.0 を超えない)
        value = sm.apply_delta("A", "B", EmotionType.AFFECTION, 0.5)
        assert value == MAX_VALUE

        # 下限クランプ (-1.0 を下回らない)
        sm2 = EmotionalStateMachine()
        sm2.apply_delta("A", "B", EmotionType.TRUST, -0.7)
        value = sm2.apply_delta("A", "B", EmotionType.TRUST, -0.7)
        assert value == MIN_VALUE

    def test_get_state(self):
        """ペア指定の状態取得。"""
        sm = EmotionalStateMachine()
        sm.apply_delta("A", "B", EmotionType.AFFECTION, 0.5)
        sm.apply_delta("A", "B", EmotionType.TENSION, 0.8)
        sm.apply_delta("B", "A", EmotionType.FEAR, 0.2)  # 逆ペアは別

        state = sm.get_state("A", "B")
        assert state[EmotionType.AFFECTION] == 0.5
        assert state[EmotionType.TENSION] == 0.8
        assert EmotionType.FEAR not in state

    def test_get_value_missing_returns_zero(self):
        """存在しない状態は 0.0。"""
        sm = EmotionalStateMachine()
        assert sm.get_value("X", "Y", EmotionType.AFFECTION) == 0.0

    def test_decay_all(self):
        """全状態の減衰 (キーごとの decay_per_episode 使用)。"""
        sm = EmotionalStateMachine()
        sm.apply_delta("A", "B", EmotionType.AFFECTION, 0.8, decay_per_episode=0.1)
        sm.apply_delta("A", "B", EmotionType.TENSION, -0.4, decay_per_episode=0.1)

        sm.decay_all(1.0)  # factor=1.0 → キーごとの decay を使用
        assert sm.get_value("A", "B", EmotionType.AFFECTION) == pytest.approx(0.72)
        assert sm.get_value("A", "B", EmotionType.TENSION) == pytest.approx(-0.36)

    def test_decay_all_uniform_factor(self):
        """一律係数モード (factor < 1.0)。"""
        sm = EmotionalStateMachine()
        sm.apply_delta("A", "B", EmotionType.AFFECTION, 0.8)
        sm.apply_delta("A", "B", EmotionType.TENSION, -0.4)

        sm.decay_all(0.5)
        assert sm.get_value("A", "B", EmotionType.AFFECTION) == pytest.approx(0.4)
        assert sm.get_value("A", "B", EmotionType.TENSION) == pytest.approx(-0.2)

    def test_decay_clamps_to_zero_direction(self):
        """減衰は 0 方向へ収束 (負の値も 0 に近づく)。"""
        sm = EmotionalStateMachine()
        sm.apply_delta("A", "B", EmotionType.TRUST, -0.8, decay_per_episode=0.75)
        sm.decay_all(1.0)
        assert sm.get_value("A", "B", EmotionType.TRUST) == pytest.approx(-0.2)

    def test_decay_episodes_passed(self):
        """複数話分の減衰。"""
        sm = EmotionalStateMachine()
        sm.apply_delta("A", "B", EmotionType.AFFECTION, 0.8, decay_per_episode=0.1)
        sm.decay_all(1.0, episodes_passed=2)
        # 0.8 * 0.9^2 = 0.648
        assert sm.get_value("A", "B", EmotionType.AFFECTION) == pytest.approx(0.648)

    def test_snapshot_and_restore(self):
        """スナップショット保存・復元。"""
        sm = EmotionalStateMachine()
        sm.apply_delta("A", "B", EmotionType.AFFECTION, -0.6)
        sm.apply_delta("A", "B", EmotionType.TENSION, 0.8)
        sm.apply_delta("B", "C", EmotionType.TRUST, 0.5)

        snapshot = sm.snapshot()
        assert snapshot["A->B"] == {"affection": -0.6, "tension": 0.8}
        assert snapshot["B->C"] == {"trust": 0.5}

        # 復元
        sm2 = EmotionalStateMachine()
        sm2.restore(snapshot)
        assert sm2.get_value("A", "B", EmotionType.AFFECTION) == -0.6
        assert sm2.get_value("A", "B", EmotionType.TENSION) == 0.8
        assert sm2.get_value("B", "C", EmotionType.TRUST) == 0.5

    def test_decay_snapshot_roundtrip(self):
        """減衰スナップショットの往復。"""
        sm = EmotionalStateMachine()
        sm.apply_delta("A", "B", EmotionType.AFFECTION, -0.6, decay_per_episode=0.07)

        decay_snap = sm.decay_snapshot()
        assert decay_snap["A->B"]["affection"] == 0.07

        sm2 = EmotionalStateMachine()
        sm2.restore(sm.snapshot(), decays=decay_snap)
        # 復元後もキーごとの decay が維持される
        sm2.decay_all(1.0)
        assert sm2.get_value("A", "B", EmotionType.AFFECTION) == pytest.approx(-0.6 * 0.93)

    def test_set_value(self):
        """直接設定。"""
        sm = EmotionalStateMachine()
        sm.set_value("A", "B", EmotionType.INTIMACY, 0.9)
        assert sm.get_value("A", "B", EmotionType.INTIMACY) == 0.9
        # クランプ
        sm.set_value("A", "B", EmotionType.INTIMACY, 5.0)
        assert sm.get_value("A", "B", EmotionType.INTIMACY) == MAX_VALUE

    def test_clear(self):
        """クリア。"""
        sm = EmotionalStateMachine()
        sm.apply_delta("A", "B", EmotionType.AFFECTION, 0.5)
        assert len(sm) == 1
        sm.clear()
        assert len(sm) == 0
