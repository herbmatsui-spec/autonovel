"""Metrics Collector for DAG Scheduler Observability (Step 4)."""
from __future__ import annotations

from typing import Protocol, Dict
from dataclasses import dataclass


@dataclass
class TaskMetrics:
    """タスク実行メトリクス。"""
    task_id: str
    dag_id: str
    duration_seconds: float
    status: str  # completed/failed/retried
    retry_count: int
    worker_id: str
    resource_usage: Dict[str, float]  # cpu, ram, gpu


class MetricsCollector(Protocol):
    """メトリクス収集のプロトコル。"""
    def record_task_start(self, task_id: str, dag_id: str, worker_id: str) -> None:
        ...
    
    def record_task_end(self, metrics: TaskMetrics) -> None:
        ...
    
    def record_queue_depth(self, dag_id: str, ready: int, running: int, pending: int) -> None:
        ...
    
    def record_resource_utilization(self, cpu_pct: float, ram_pct: float, gpu_pct: float) -> None:
        ...
    
    def record_retry(self, task_id: str, attempt: int) -> None:
        ...


class NoOpMetricsCollector:
    """何もしないデフォルト実装。"""
    def record_task_start(self, task_id: str, dag_id: str, worker_id: str) -> None:
        pass
    
    def record_task_end(self, metrics: TaskMetrics) -> None:
        pass
    
    def record_queue_depth(self, dag_id: str, ready: int, running: int, pending: int) -> None:
        pass
    
    def record_resource_utilization(self, cpu_pct: float, ram_pct: float, gpu_pct: float) -> None:
        pass
    
    def record_retry(self, task_id: str, attempt: int) -> None:
        pass


# Prometheus 実装 (オプション依存)
try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Histogram = Gauge = object  # type: ignore


class PrometheusMetricsCollector:
    """Prometheus メトリクス出力。"""
    def __init__(self, namespace: str = "dag_scheduler"):
        if not PROMETHEUS_AVAILABLE:
            raise RuntimeError("prometheus_client not installed. Install with: pip install prometheus-client")
        
        self.task_duration = Histogram(
            "task_duration_seconds", "Task execution duration",
            ["dag_id", "status"], namespace=namespace
        )
        self.queue_depth = Gauge(
            "queue_depth", "Number of tasks in each state",
            ["dag_id", "state"], namespace=namespace
        )
        self.resource_util = Gauge(
            "resource_utilization_percent", "Resource utilization",
            ["resource"], namespace=namespace
        )
        self.retry_counter = Counter(
            "task_retries_total", "Total retry attempts",
            ["task_id"], namespace=namespace
        )
    
    def record_task_start(self, task_id: str, dag_id: str, worker_id: str) -> None:
        pass  # 開始時刻は内部保持
    
    def record_task_end(self, metrics: TaskMetrics) -> None:
        self.task_duration.labels(dag_id=metrics.dag_id, status=metrics.status).observe(
            metrics.duration_seconds
        )
    
    def record_queue_depth(self, dag_id: str, ready: int, running: int, pending: int) -> None:
        self.queue_depth.labels(dag_id=dag_id, state="ready").set(ready)
        self.queue_depth.labels(dag_id=dag_id, state="running").set(running)
        self.queue_depth.labels(dag_id=dag_id, state="pending").set(pending)
    
    def record_resource_utilization(self, cpu_pct: float, ram_pct: float, gpu_pct: float) -> None:
        self.resource_util.labels(resource="cpu").set(cpu_pct)
        self.resource_util.labels(resource="ram").set(ram_pct)
        self.resource_util.labels(resource="gpu").set(gpu_pct)
    
    def record_retry(self, task_id: str, attempt: int) -> None:
        self.retry_counter.labels(task_id=task_id).inc()


# OpenTelemetry トレーシング (オプション依存)
try:
    from opentelemetry import trace
    from opentelemetry.trace import SpanKind
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    SpanKind = None


class OTELTracingCollector:
    """OpenTelemetry 分散トレーシング連携。"""
    def __init__(self, tracer_name: str = "dag_scheduler"):
        if not OTEL_AVAILABLE:
            raise RuntimeError("opentelemetry-api not installed. Install with: pip install opentelemetry-api")
        self.tracer = trace.get_tracer(tracer_name)
    
    def trace_task(self, task_id: str, dag_id: str, fn):
        """タスク実行をスパンで包むデコレータ。"""
        def wrapper(*args, **kwargs):
            with self.tracer.start_as_current_span(
                f"task.{task_id}", kind=SpanKind.INTERNAL
            ) as span:
                span.set_attribute("dag.id", dag_id)
                span.set_attribute("task.id", task_id)
                return fn(*args, **kwargs)
        return wrapper


__all__ = [
    "MetricsCollector",
    "TaskMetrics",
    "NoOpMetricsCollector",
    "PrometheusMetricsCollector",
    "OTELTracingCollector",
    "PROMETHEUS_AVAILABLE",
    "OTEL_AVAILABLE",
]