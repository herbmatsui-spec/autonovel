"""Regression check script for CI integration."""
from __future__ import annotations

import argparse
import sys
import yaml
from pathlib import Path
from typing import Any, Dict

from tests.benchmarks.metrics import check_regression, compute_scaling_metrics
from tests.benchmarks.report import load_json


def load_thresholds(path: str) -> Dict[str, Any]:
    """Load thresholds from YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_results(
    results_path: str,
    thresholds_path: str = "tests/benchmarks/thresholds.yaml",
    checkpoint: int = None,
) -> int:
    """Check benchmark results against thresholds. Returns 0 on pass, 1 on fail."""
    # Load data
    data = load_json(results_path)
    thresholds = load_thresholds(thresholds_path)

    # Determine which checkpoint to check
    checkpoints = data.get("checkpoints", {})
    if not checkpoints:
        print("ERROR: No checkpoints found in results", file=sys.stderr)
        return 1

    if checkpoint is None:
        checkpoint = max(checkpoints.keys())

    if checkpoint not in checkpoints:
        print(f"ERROR: Checkpoint {checkpoint} not found. Available: {list(checkpoints.keys())}", file=sys.stderr)
        return 1

    summary = checkpoints[checkpoint]

    # Check overall regression
    base_thresholds = {
        "max_latency_ms_per_ep": thresholds.get("max_latency_ms_per_ep", 5000),
        "min_compression_ratio": thresholds.get("min_compression_ratio", 0.6),
        "max_memory_mb": thresholds.get("max_memory_mb", 100),
        "min_cache_hit_rate": thresholds.get("min_cache_hit_rate", 0.5),
    }

    # Check scene-specific thresholds
    scene_violations = []
    scene_bd = summary.get("scene_breakdown", {})
    scene_thresholds = thresholds.get("scene_thresholds", {})

    for scene, metrics in scene_bd.items():
        if scene in scene_thresholds:
            st = scene_thresholds[scene]
            scene_base = {
                "max_latency_ms_per_ep": st.get("max_latency_ms_per_ep", base_thresholds["max_latency_ms_per_ep"]),
                "min_compression_ratio": st.get("min_compression_ratio", base_thresholds["min_compression_ratio"]),
                "max_memory_mb": base_thresholds["max_memory_mb"],
                "min_cache_hit_rate": base_thresholds["min_cache_hit_rate"],
            }
            result = check_regression(metrics, scene_base)
            if not result["passed"]:
                for v in result["violations"]:
                    v["scene"] = scene
                    scene_violations.append(v)

    # Check scaling metrics
    scaling_violations = []
    scaling = compute_scaling_metrics(checkpoints)
    if scaling:
        max_latency_scaling = thresholds.get("max_latency_scaling_ms_per_ep", 100)
        max_memory_scaling = thresholds.get("max_memory_scaling_mb_per_ep", 0.5)

        if scaling["latency_per_episode_ms"] > max_latency_scaling:
            scaling_violations.append({
                "metric": "latency_scaling",
                "value": scaling["latency_per_episode_ms"],
                "threshold": max_latency_scaling,
                "severity": "warning",
            })
        if scaling["memory_per_episode_mb"] > max_memory_scaling:
            scaling_violations.append({
                "metric": "memory_scaling",
                "value": scaling["memory_per_episode_mb"],
                "threshold": max_memory_scaling,
                "severity": "warning",
            })

    # Overall check
    overall_result = check_regression(summary, base_thresholds)

    # Collect all violations
    all_violations = overall_result["violations"] + scene_violations + scaling_violations

    # Print results
    print(f"Regression Check: {results_path} (checkpoint: {checkpoint} episodes)")
    print("=" * 60)

    if overall_result["passed"] and not scene_violations and not scaling_violations:
        print("✓ ALL CHECKS PASSED")
        print(f"  Episodes: {summary.get('episode_count', 0)}")
        print(f"  Latency (p95): {summary.get('latency_ms', {}).get('p95', 0):.1f}ms")
        print(f"  Reduction (mean): {summary.get('reduction_ratio', {}).get('mean', 0):.1%}")
        print(f"  Memory (max): {summary.get('memory_mb', {}).get('max', 0):.1f}MB")
        print(f"  Cache Hit Rate: {summary.get('cache_hit_rate', 0):.1%}")
        if scaling:
            print(f"  Latency Scaling: {scaling['latency_per_episode_ms']:.2f} ms/ep")
            print(f"  Memory Scaling:  {scaling['memory_per_episode_mb']:.4f} MB/ep")
        return 0
    else:
        print("✗ REGRESSION DETECTED")
        print()

        if overall_result["violations"]:
            print("OVERALL VIOLATIONS:")
            for v in overall_result["violations"]:
                print(f"  - {v['metric']}: {v['value']:.2f} > {v['threshold']:.2f} ({v['severity']})")
            print()

        if scene_violations:
            print("SCENE-SPECIFIC VIOLATIONS:")
            for v in scene_violations:
                print(f"  - [{v['scene']}] {v['metric']}: {v['value']:.2f} > {v['threshold']:.2f} ({v['severity']})")
            print()

        if scaling_violations:
            print("SCALING VIOLATIONS:")
            for v in scaling_violations:
                print(f"  - {v['metric']}: {v['value']:.2f} > {v['threshold']:.2f} ({v['severity']})")
            print()

        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check benchmark results for regressions",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "results_file",
        type=str,
        help="Path to benchmark results JSON file",
    )
    parser.add_argument(
        "--thresholds",
        type=str,
        default="tests/benchmarks/thresholds.yaml",
        help="Path to thresholds YAML file",
    )
    parser.add_argument(
        "--checkpoint",
        type=int,
        default=None,
        help="Specific episode checkpoint to check (default: max)",
    )

    args = parser.parse_args()

    if not Path(args.results_file).exists():
        print(f"ERROR: Results file not found: {args.results_file}", file=sys.stderr)
        return 1

    if not Path(args.thresholds).exists():
        print(f"ERROR: Thresholds file not found: {args.thresholds}", file=sys.stderr)
        return 1

    return check_results(args.results_file, args.thresholds, args.checkpoint)


if __name__ == "__main__":
    sys.exit(main())