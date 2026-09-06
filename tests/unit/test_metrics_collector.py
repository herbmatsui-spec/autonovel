"""Tests for Metrics Collector (Step 4)."""
import pytest
from src.backend.tasks.metrics_collector import (
    NoOpMetricsCollector,
    PrometheusMetricsCollector,
    TaskMetrics,
    PROMETHEUS_AVAILABLE,
)


def test_noop_collector_does_nothing():
    """NoOpMetricsCollector は何もしない（例外なし）。"""
    c = NoOpMetricsCollector()
    c.record_task_start("t1", "dag1", "w1")
    c.record_task_end(TaskMetrics("t1", "dag1", 1.0, "completed", 0, "w1", {}))
    c.record_queue_depth("dag1", 1, 2, 3)
    c.record_resource_utilization(50.0, 60.0, 0.0)
    c.record_retry("t1", 1)
    # 例外なし = 成功


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_prometheus_collector_records():
    """PrometheusMetricsCollector がメトリクスを記録する。"""
    c = PrometheusMetricsCollector()
    c.record_task_end(TaskMetrics("t1", "dag1", 1.5, "completed", 0, "w1", {}))
    c.record_queue_depth("dag1", 2, 1, 3)
    c.record_resource_utilization(50.0, 60.0, 70.0)
    c.record_retry("t1", 1)
    # メトリクス登録確認（内部属性で確認）
    assert c.task_duration._metrics  # type: ignore
    assert c.queue_depth._metrics  # type: ignore
    assert c.resource_util._metrics  # type: ignore
    assert c.retry_counter._metrics  # type: ignore


def test_task_metrics_dataclass():
    """TaskMetrics データクラスが正しく構築される。"""
    m = TaskMetrics(
        task_id="t1",
        dag_id="dag1",
        duration_seconds=2.5,
        status="completed",
        retry_count=1,
        worker_id="w1",
        resource_usage={"cpu": 1.0, "ram": 512, "gpu": 0}
    )
    assert m.task_id == "t1"
    assert m.duration_seconds == 2.5
    assert m.status == "completed"
    assert m.resource_usage["cpu"] == 1.0