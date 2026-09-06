"""Report generation and output for benchmarks."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from datetime import datetime


def format_value(v: Any, precision: int = 2) -> str:
    """Format a value for display."""
    if isinstance(v, float):
        return f"{v:.{precision}f}"
    return str(v)


def format_pct_stats(stats: Dict[str, float], unit: str = "") -> str:
    """Format percentile stats as a compact string."""
    if not stats:
        return "N/A"
    return f"mean={format_value(stats.get('mean', 0))}{unit}, p50={format_value(stats.get('p50', 0))}{unit}, p95={format_value(stats.get('p95', 0))}{unit}"


def print_report(summary: Dict[str, Any], title: str = "Benchmark Report") -> None:
    """Print a formatted benchmark report to stdout."""
    print("=" * 70)
    print(f" {title}")
    print("=" * 70)
    print(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Episodes:  {summary.get('episode_count', 0)}")
    print("-" * 70)

    # Overall metrics
    print(" OVERALL METRICS:")
    print(f"  Latency:     {format_pct_stats(summary.get('latency_ms'), 'ms')}")
    print(f"  Memory:      {format_pct_stats(summary.get('memory_mb'), 'MB')}")
    print(f"  Final Tokens: {format_pct_stats(summary.get('final_tokens'))}")
    print(f"  Reduction:   {format_pct_stats(summary.get('reduction_ratio'))}")
    print(f"  Cache Hit:   {format_value(summary.get('cache_hit_rate', 0) * 100, 1)}%")
    print("-" * 70)

    # Scene breakdown
    scene_bd = summary.get("scene_breakdown", {})
    if scene_bd:
        print(" PER SCENE TYPE:")
        for scene, metrics in sorted(scene_bd.items()):
            print(f"  {scene:15s} (n={metrics['count']}): "
                  f"latency={format_pct_stats(metrics.get('latency_ms'), 'ms')}, "
                  f"reduction={format_pct_stats(metrics.get('reduction_ratio'))}, "
                  f"tokens={format_pct_stats(metrics.get('final_tokens'))}")
        print("-" * 70)


def print_checkpoints_report(checkpoints: Dict[int, Dict[str, Any]]) -> None:
    """Print report for multiple checkpoints."""
    print("=" * 70)
    print(" CHECKPOINT COMPARISON")
    print("=" * 70)
    print(f" {'Episodes':>8} | {'Latency(ms)':>15} | {'Reduction':>10} | {'Tokens':>8} | {'Cache%':>6}")
    print("-" * 70)
    for cp in sorted(checkpoints.keys()):
        data = checkpoints[cp]
        lat = format_value(data.get('latency_ms', {}).get('mean', 0))
        red = format_value(data.get('reduction_ratio', {}).get('mean', 0) * 100, 1)
        tok = format_value(data.get('final_tokens', {}).get('mean', 0))
        ch = format_value(data.get('cache_hit_rate', 0) * 100, 1)
        print(f" {cp:>8} | {lat:>15} | {red:>9}% | {tok:>8} | {ch:>5}%")
    print("-" * 70)


def save_json(data: Dict[str, Any], path: str) -> None:
    """Save benchmark results to JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    print(f"Results saved to: {path}")


def load_json(path: str) -> Dict[str, Any]:
    """Load benchmark results from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_markdown_report(
    summary: Dict[str, Any],
    title: str = "Benchmark Report",
    checkpoints: Optional[Dict[int, Dict[str, Any]]] = None,
) -> str:
    """Generate a Markdown formatted report."""
    lines = []
    lines.append(f"# {title}")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Episodes: {summary.get('episode_count', 0)}")
    lines.append("\n## Overall Metrics")
    lines.append("| Metric | Mean | P50 | P95 | Min | Max |")
    lines.append("|--------|------|-----|-----|-----|-----|")

    for metric_name in ["latency_ms", "memory_mb", "final_tokens", "reduction_ratio"]:
        stats = summary.get(metric_name, {})
        unit = "ms" if metric_name == "latency_ms" else ("MB" if metric_name == "memory_mb" else "")
        lines.append(f"| {metric_name} | {format_value(stats.get('mean', 0))}{unit} | "
                     f"{format_value(stats.get('p50', 0))}{unit} | {format_value(stats.get('p95', 0))}{unit} | "
                     f"{format_value(stats.get('min', 0))}{unit} | {format_value(stats.get('max', 0))}{unit} |")

    lines.append(f"\n| Cache Hit Rate | {format_value(summary.get('cache_hit_rate', 0) * 100, 1)}% | | | | |")

    # Scene breakdown
    scene_bd = summary.get("scene_breakdown", {})
    if scene_bd:
        lines.append("\n## Per Scene Type")
        lines.append("| Scene | Count | Latency (ms) | Reduction | Final Tokens |")
        lines.append("|-------|-------|--------------|-----------|--------------|")
        for scene, metrics in sorted(scene_bd.items()):
            lines.append(f"| {scene} | {metrics['count']} | "
                         f"{format_pct_stats(metrics.get('latency_ms'), 'ms')} | "
                         f"{format_pct_stats(metrics.get('reduction_ratio'))} | "
                         f"{format_pct_stats(metrics.get('final_tokens'))} |")

    # Checkpoints
    if checkpoints:
        lines.append("\n## Checkpoints")
        lines.append("| Episodes | Latency (ms) | Reduction | Final Tokens | Cache Hit |")
        lines.append("|----------|--------------|-----------|--------------|-----------|")
        for cp in sorted(checkpoints.keys()):
            data = checkpoints[cp]
            lines.append(f"| {cp} | {format_value(data.get('latency_ms', {}).get('mean', 0))} | "
                         f"{format_value(data.get('reduction_ratio', {}).get('mean', 0) * 100, 1)}% | "
                         f"{format_value(data.get('final_tokens', {}).get('mean', 0))} | "
                         f"{format_value(data.get('cache_hit_rate', 0) * 100, 1)}% |")

    return "\n".join(lines)


def save_markdown_report(
    summary: Dict[str, Any],
    path: str,
    title: str = "Benchmark Report",
    checkpoints: Optional[Dict[int, Dict[str, Any]]] = None,
) -> None:
    """Save markdown report to file."""
    md = generate_markdown_report(summary, title, checkpoints)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Markdown report saved to: {path}")


__all__ = [
    "print_report",
    "print_checkpoints_report",
    "save_json",
    "load_json",
    "generate_markdown_report",
    "save_markdown_report",
]