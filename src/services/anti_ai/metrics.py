"""Prometheus metrics for anti-AI detection and correction."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

anti_ai_detection_total = Counter(
    "anti_ai_detection_total",
    "Total number of anti-AI detections",
    ["category", "method"],
)

anti_ai_corrections_total = Counter(
    "anti_ai_corrections_total",
    "Total number of corrections applied",
    ["category"],
)

anti_ai_loop_iterations = Histogram(
    "anti_ai_loop_iterations",
    "Number of iterations per correction loop",
    buckets=[1, 2, 3, 5, 10],
)

anti_ai_score = Gauge(
    "anti_ai_score",
    "Current anti-AI score after correction",
)


def record_detection(category: str, method: str = "rule_based") -> None:
    """Record a detection event."""
    anti_ai_detection_total.labels(category=category, method=method).inc()


def record_correction(category: str) -> None:
    """Record a correction event."""
    anti_ai_corrections_total.labels(category=category).inc()


def record_loop_iterations(iterations: int) -> None:
    """Record the number of iterations in a loop."""
    anti_ai_loop_iterations.observe(iterations)


def set_score(score: float) -> None:
    """Set the current anti-AI score."""
    anti_ai_score.set(score)
