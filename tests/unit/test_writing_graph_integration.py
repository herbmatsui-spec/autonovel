"""
WritingGraphManager と StreamingPlotScheduler の統合テスト

依存関係管理 (run_with_dependencies / _check_dependency / _wait_for_dependency)
がスケジューラなし・ありの両方で安全に動作することを確認する。
"""

import asyncio

import pytest

from src.backend.workflows.writing_langgraph import WritingGraphManager


class _FakePlot:
    def __init__(self, ep_num, blueprint="十分に長い設計図" * 10):
        self.ep_num = ep_num
        self.detailed_blueprint = blueprint


class _FakeRepo:
    def __init__(self, plots=None):
        self._plots = plots or {}

    async def get_plot(self, branch_id, ep_num):
        return self._plots.get(ep_num)


class _FakeScheduler:
    """await_plot_ready のみを実装した軽量フェイク"""

    def __init__(self):
        self.waited = []

    async def await_plot_ready(self, ep_num):
        self.waited.append(ep_num)
        return _FakePlot(ep_num)


@pytest.fixture
def manager():
    m = WritingGraphManager.__new__(WritingGraphManager)
    m.manager = None
    m.workflow = None
    m.checkpointer = None
    m._checkpoint_metadata = {}
    m._scheduler = None
    from src.backend.workflows.quality_metrics import QualityMetricsCollector
    m.metrics_collector = QualityMetricsCollector()
    return m


@pytest.mark.anyio
async def test_run_with_dependencies_no_scheduler(manager):
    """スケジューラ未注入でも依存チェックは許可され、run に到達する"""
    # run() は実際の LLM 呼び出しを行うため、ここでは依存チェック部分のみ検証
    ok = await manager._check_dependency(2, 1)
    assert ok is True  # 記録なしは許可
    await manager._wait_for_dependency(2, 1)  # 何も起きない


@pytest.mark.anyio
async def test_check_dependency_low_quality(manager):
    from src.backend.workflows.quality_metrics import QualityMetrics
    m = QualityMetrics(1, True, False, 0.0, 1, 70, 1.0, genre="x", dogfeed_ok=False)
    manager.metrics_collector.record(m)
    ok = await manager._check_dependency(2, 1)
    assert ok is False  # 低品質は拒否


@pytest.mark.anyio
async def test_wait_for_dependency_with_scheduler(manager):
    sched = _FakeScheduler()
    manager.set_scheduler(sched)
    await manager._wait_for_dependency(3, 2)
    assert sched.waited == [2]


@pytest.mark.anyio
async def test_set_scheduler_idempotent(manager):
    sched = _FakeScheduler()
    manager.set_scheduler(sched)
    assert manager._scheduler is sched
    manager.set_scheduler(None)
    assert manager._scheduler is None
