"""Metrics aggregation and analysis for benchmarks."""
from __future__ import annotations

from typing import Any, Dict, List
from tests.benchmarks.utils import mean, percentile


def aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate benchmark results across episodes."""
    if not results:
        return {}

    latencies = [r["latency_ms"]["mean"] for r in results]
    memories = [r["memory_mb"]["mean"] for r in results]
    final_tokens = [r["final_tokens"]["mean"] for r in results]
    reductions = [r["reduction_ratio"]["mean"] for r in results]
    cache_hits = [r["cache_hit_rate"] for r in results]

    def pct_stats(values: List[float]) -> Dict[str, float]:
        return {
            "mean": mean(values),
            "p50": percentile(values, 50),
            "p95": percentile(values, 95),
            "min": min(values),
            "max": max(values),
        }

    # Per scene type breakdown
    scene_types = {}
    for r in results:
        st = r["scene_type"]
        if st not in scene_types:
            scene_types[st] = []
        scene_types[st].append(r)

    scene_breakdown = {}
    for st, st_results in scene_types.items():
        scene_breakdown[st] = {
            "count": len(st_results),
            "latency_ms": pct_stats([r["latency_ms"]["mean"] for r in st_results]),
            "reduction_ratio": pct_stats([r["reduction_ratio"]["mean"] for r in st_results]),
            "final_tokens": pct_stats([r["final_tokens"]["mean"] for r in st_results]),
            "cache_hit_rate": mean([r["cache_hit_rate"] for r in st_results]),
        }

    return {
        "episode_count": len(results),
        "latency_ms": pct_stats(latencies),
        "memory_mb": pct_stats(memories),
        "final_tokens": pct_stats(final_tokens),
        "reduction_ratio": pct_stats(reductions),
        "cache_hit_rate": mean(cache_hits),
        "scene_breakdown": scene_breakdown,
    }


def aggregate_by_episode_count(
    all_results: List[Dict[str, Any]],
    ep_counts: List[int],
) -> Dict[int, Dict[str, Any]]:
    """Aggregate results at specific episode count checkpoints."""
    checkpoints = {}
    for cp in ep_counts:
        cp_results = [r for r in all_results if r["ep_num"] <= cp]
        if cp_results:
            checkpoints[cp] = aggregate_results(cp_results)
    return checkpoints


def compute_scaling_metrics(
    checkpoints: Dict[Any, Dict[str, Any]],
) -> Dict[str, Any]:
    """Compute scaling behavior metrics (linear, quadratic, etc.)."""
    if len(checkpoints) < 2:
        return {}

    ep_counts = sorted(int(k) for k in checkpoints.keys())

    # Handle both string and int keys
    def get_cp(cp):
        if cp in checkpoints:
            return checkpoints[cp]
        return checkpoints[str(cp)]
    
    latencies = [get_cp(cp)["latency_ms"]["mean"] for cp in ep_counts]
    memories = [get_cp(cp)["memory_mb"]["mean"] for cp in ep_counts]

    # Simple linear regression slope (latency per episode)
    n = len(ep_counts)
    sum_x = sum(ep_counts)
    sum_y = sum(latencies)
    sum_xy = sum(x * y for x, y in zip(ep_counts, latencies))
    sum_x2 = sum(x * x for x in ep_counts)

    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if n * sum_x2 != sum_x * sum_x else 0
    intercept = (sum_y - slope * sum_x) / n

    # Memory scaling
    sum_y_mem = sum(memories)
    sum_xy_mem = sum(x * y for x, y in zip(ep_counts, memories))
    slope_mem = (n * sum_xy_mem - sum_x * sum_y_mem) / (n * sum_x2 - sum_x * sum_x) if n * sum_x2 != sum_x * sum_x else 0

    return {
        "latency_per_episode_ms": slope,
        "latency_intercept_ms": intercept,
        "memory_per_episode_mb": slope_mem,
        "episodes_analyzed": ep_counts,
    }


def check_regression(
    summary: Dict[str, Any],
    thresholds: Dict[str, float],
) -> Dict[str, Any]:
    """Check if metrics exceed regression thresholds."""
    violations = []

    # Latency check
    if "latency_ms" in summary:
        p95_latency = summary["latency_ms"].get("p95", 0)
        max_latency = thresholds.get("max_latency_ms_per_ep", float("inf"))
        if p95_latency > max_latency:
            violations.append({
                "metric": "latency_p95_ms",
                "value": p95_latency,
                "threshold": max_latency,
                "severity": "error",
            })

    # Compression ratio check
    if "reduction_ratio" in summary:
        mean_reduction = summary["reduction_ratio"].get("mean", 0)
        min_reduction = thresholds.get("min_compression_ratio", 0)
        if mean_reduction < min_reduction:
            violations.append({
                "metric": "compression_ratio",
                "value": mean_reduction,
                "threshold": min_reduction,
                "severity": "error",
            })

    # Memory check
    if "memory_mb" in summary:
        max_memory = summary["memory_mb"].get("max", 0)
        max_mem_threshold = thresholds.get("max_memory_mb", float("inf"))
        if max_memory > max_mem_threshold:
            violations.append({
                "metric": "memory_max_mb",
                "value": max_memory,
                "threshold": max_mem_threshold,
                "severity": "warning",
            })

    # Cache hit rate check
    cache_hit = summary.get("cache_hit_rate", 0)
    min_cache = thresholds.get("min_cache_hit_rate", 0)
    if cache_hit < min_cache:
        violations.append({
            "metric": "cache_hit_rate",
            "value": cache_hit,
            "threshold": min_cache,
            "severity": "warning",
        })

    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "summary": {
            "total_checks": len(thresholds),
            "passed_checks": len(thresholds) - len(violations),
        },
    }


__all__ = [
    "aggregate_results",
    "aggregate_by_episode_count",
    "compute_scaling_metrics",
    "check_regression",
]