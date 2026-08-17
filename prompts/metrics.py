from __future__ import annotations

import abc
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class PromptMetric:
    """個別テンプレートのメトリクス。"""

    template_name: str
    hits: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    last_accessed: float | None = None
    error_count: int = 0


class IMetricsCollector(abc.ABC):
    """メトリクスコレクタのインターフェース。"""

    @abc.abstractmethod
    def record_hit(self, template_name: str, duration_ms: float = 0.0, error: bool = False) -> None:
        """テンプレートアクセスを記録する。"""
        ...

    @abc.abstractmethod
    def get_metrics(self) -> dict[str, PromptMetric]:
        """現在のメトリクススナップショットを取得する。"""
        ...

    @abc.abstractmethod
    def reset_metrics(self) -> None:
        """全メトリクスをリセットする。"""
        ...

    @abc.abstractmethod
    def flush(self) -> None:
        """バッファをフラッシュする（外部システムへの送信等）。"""
        ...


class InMemoryCollector(IMetricsCollector):
    """インメモリ実装（既存の動作を維持）。"""

    def __init__(self):
        self._metrics: dict[str, PromptMetric] = {}

    def _init_metric(self, template_name: str) -> None:
        if template_name not in self._metrics:
            self._metrics[template_name] = PromptMetric(template_name=template_name)

    def record_hit(self, template_name: str, duration_ms: float = 0.0, error: bool = False) -> None:
        self._init_metric(template_name)
        metric = self._metrics[template_name]
        metric.hits += 1
        metric.total_time_ms += duration_ms
        metric.avg_time_ms = metric.total_time_ms / metric.hits
        metric.last_accessed = time.time()
        if error:
            metric.error_count += 1

    def get_metrics(self) -> dict[str, PromptMetric]:
        return dict(self._metrics)

    def reset_metrics(self) -> None:
        self._metrics.clear()

    def flush(self) -> None:
        pass


class PrometheusCollector(IMetricsCollector):
    """Prometheus Client 用のコレクタ（prometheus_client が必要）。"""

    def __init__(self):
        try:
            from prometheus_client import Counter, Histogram
        except ImportError:
            raise RuntimeError("prometheus_client is not installed. Run: pip install prometheus_client")

        self._hits = Counter(
            "prompt_template_hits_total",
            "Total number of prompt template hits",
            ["template_name", "status"],
        )
        self._duration = Histogram(
            "prompt_template_render_duration_seconds",
            "Prompt template render duration in seconds",
            ["template_name"],
        )
        self._local: dict[str, PromptMetric] = {}

    def _init_metric(self, template_name: str) -> None:
        if template_name not in self._local:
            self._local[template_name] = PromptMetric(template_name=template_name)

    def record_hit(self, template_name: str, duration_ms: float = 0.0, error: bool = False) -> None:
        self._init_metric(template_name)
        metric = self._local[template_name]
        metric.hits += 1
        metric.total_time_ms += duration_ms
        metric.avg_time_ms = metric.total_time_ms / metric.hits
        metric.last_accessed = time.time()
        if error:
            metric.error_count += 1

        status = "error" if error else "success"
        self._hits.labels(template_name=template_name, status=status).inc()
        self._duration.labels(template_name=template_name).observe(duration_ms / 1000.0)

    def get_metrics(self) -> dict[str, PromptMetric]:
        return dict(self._local)

    def reset_metrics(self) -> None:
        self._local.clear()

    def flush(self) -> None:
        pass


class DatabaseCollector(IMetricsCollector):
    """DB への定期書き込み用コレクタ（UnitOfWork 経由）。"""

    def __init__(self, db_manager: Any, flush_interval: int = 60):
        self.db_manager = db_manager
        self.flush_interval = flush_interval
        self._local: dict[str, PromptMetric] = {}
        self._last_flush = time.time()

    def _init_metric(self, template_name: str) -> None:
        if template_name not in self._local:
            self._local[template_name] = PromptMetric(template_name=template_name)

    def record_hit(self, template_name: str, duration_ms: float = 0.0, error: bool = False) -> None:
        self._init_metric(template_name)
        metric = self._local[template_name]
        metric.hits += 1
        metric.total_time_ms += duration_ms
        metric.avg_time_ms = metric.total_time_ms / metric.hits
        metric.last_accessed = time.time()
        if error:
            metric.error_count += 1

        if time.time() - self._last_flush >= self.flush_interval:
            self.flush()

    def get_metrics(self) -> dict[str, PromptMetric]:
        return dict(self._local)

    def reset_metrics(self) -> None:
        self._local.clear()

    def flush(self) -> None:
        if not self._local:
            return
        try:
            from sqlalchemy import insert

            from src.backend.database.models import PromptMetrics as PromptMetricsModel

            with self.db_manager.get_session() as session:
                for metric in self._local.values():
                    stmt = insert(PromptMetricsModel).values(
                        template_name=metric.template_name,
                        hits=metric.hits,
                        total_time_ms=metric.total_time_ms,
                        avg_time_ms=metric.avg_time_ms,
                        error_count=metric.error_count,
                    )
                    session.execute(stmt)
                session.commit()
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(f"Failed to flush prompt metrics to DB: {e}")
        finally:
            self._last_flush = time.time()
