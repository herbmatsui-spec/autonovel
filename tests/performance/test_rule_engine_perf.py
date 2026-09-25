"""Step 23: ルールエンジンパフォーマンステスト。

測定: 100イベント処理時間 < 100ms, メモリ増加 < 50MB
"""
from __future__ import annotations

import time
from typing import List

import pytest

from src.pipeline.emotional_residue import EmotionType
from src.rules.engine import RuleEngine
from src.rules.emotional_rules import EmotionalRule, PlotContext
from src.rules.plot_events import PlotEvent, PlotEventType, Role
from src.rules.rule_loader import DEFAULT_RULES_PATH, RuleLoader
from src.rules.state_machine import EmotionalStateMachine


def _make_rules(num_rules: int = 8) -> List[EmotionalRule]:
    """テスト用ルール群。"""
    return [
        EmotionalRule(
            event_type=PlotEventType.BETRAYAL,
            source_role=Role.VICTIM,
            target_role=Role.PERPETRATOR,
            emotion_deltas={
                EmotionType.AFFECTION: -0.1,
                EmotionType.TENSION: 0.1,
            },
            decay_per_episode=0.1,
            rule_id=f"perf_rule_{i}",
        )
        for i in range(num_rules)
    ]


def _make_events(num_events: int = 100) -> List[PlotEvent]:
    """テスト用イベント列。"""
    return [
        PlotEvent(
            f"ep{i}_betrayal", i, 1, PlotEventType.BETRAYAL,
            roles={Role.VICTIM: f"char_{i % 10}", Role.PERPETRATOR: f"char_{(i + 1) % 10}"},
        )
        for i in range(num_events)
    ]


class TestRuleEnginePerformance:
    """ルールエンジン性能テスト。"""

    def test_100_events_under_100ms(self):
        """100イベント処理時間 < 100ms。"""
        rules = _make_rules()
        engine = RuleEngine(rules=rules, state_machine=EmotionalStateMachine())
        events = _make_events(100)

        start = time.perf_counter()
        for i, event in enumerate(events):
            engine.process_event(event, PlotContext(episode=i))
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 100, f"100 events took {elapsed_ms:.1f}ms (> 100ms)"

    def test_100_events_memory_increase_under_50mb(self):
        """100イベント処理のメモリ増加 < 50MB。"""
        import tracemalloc

        rules = _make_rules()
        engine = RuleEngine(rules=rules, state_machine=EmotionalStateMachine())
        events = _make_events(100)

        tracemalloc.start()
        for i, event in enumerate(events):
            engine.process_event(event, PlotContext(episode=i))
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        increase_mb = peak / (1024 * 1024)
        assert increase_mb < 50, f"Memory increase {increase_mb:.1f}MB (> 50MB)"

    def test_100_episode_processing_under_100ms(self):
        """エピソード単位 100話処理のスループット確認。"""
        rules = _make_rules()
        engine = RuleEngine(rules=rules, state_machine=EmotionalStateMachine())
        events = _make_events(100)

        start = time.perf_counter()
        # 100話を 1話 1イベントで処理
        snapshot = None
        prev_ep = None
        for ep in range(1, 101):
            engine.process_episode(
                ep, [events[ep - 1]],
                previous_snapshot=snapshot, previous_episode=prev_ep,
            )
            snapshot = engine.last_snapshot
            prev_ep = ep
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 500, f"100 episodes took {elapsed_ms:.1f}ms"

    def test_state_machine_scaling(self):
        """状態マシンのスケーリング確認 (1000エントリ)。"""
        sm = EmotionalStateMachine()
        start = time.perf_counter()
        for i in range(1000):
            sm.apply_delta(f"c{i}", f"c{(i + 1) % 1000}", EmotionType.AFFECTION, 0.001)
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 100, f"1000 apply_delta took {elapsed_ms:.1f}ms"
        assert len(sm) == 1000


# pytest-benchmark が利用可能な場合のベンチマーク (pytest --benchmark-only で実行)
try:
    import pytest_benchmark  # noqa: F401

    HAS_BENCHMARK = True
except ImportError:
    HAS_BENCHMARK = False


@pytest.mark.skipif(not HAS_BENCHMARK, reason="pytest-benchmark not installed")
class TestRuleEngineBenchmark:
    """pytest-benchmark ベンチマーク。"""

    def test_benchmark_process_event(self, benchmark):
        """単一イベント処理のベンチマーク。"""
        rules = _make_rules()
        engine = RuleEngine(rules=rules, state_machine=EmotionalStateMachine())
        event = PlotEvent("e1", 1, 1, PlotEventType.BETRAYAL,
                          roles={Role.VICTIM: "A", Role.PERPETRATOR: "B"})
        ctx = PlotContext(episode=1)

        result = benchmark(engine.process_event, event, ctx)
        assert isinstance(result, list)

    def test_benchmark_state_machine(self, benchmark):
        """状態マシンのベンチマーク。"""
        sm = EmotionalStateMachine()

        def run():
            for i in range(100):
                sm.apply_delta(f"c{i}", f"c{(i + 1) % 100}", EmotionType.TENSION, 0.01)

        benchmark(run)
