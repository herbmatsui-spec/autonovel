# src/backend/observability/__init__.py
"""
Observability パッケージ.

メトリクス、ヘルスチェック、その他の可観測性機能を提供する。

注意: メトリクスモジュールの循環インポートを避けるため、
メトリクスはサブモジュールから直接インポートしてください:

    from backend.observability.metrics import http_requests_total
    from backend.observability.graph_metrics import GRAPH_OPERATIONS_TOTAL
    from backend.observability.graph_metrics import init_metrics
"""

from .health import build_health_payload
from .health import metrics as health_metrics

__all__ = [
    "build_health_payload",
    "health_metrics",
]
