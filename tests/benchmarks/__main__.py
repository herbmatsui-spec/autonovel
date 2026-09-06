"""CLI entrypoint for benchmarks."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from tests.benchmarks.fixtures import generate_long_novel
from tests.benchmarks.run_multi import benchmark_novel
from tests.benchmarks.report import print_report, print_checkpoints_report, save_json, save_markdown_report
from tests.benchmarks.metrics import compute_scaling_metrics


def parse_episode_counts(s: str) -> List[int]:
    """Parse comma-separated episode counts."""
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="4-Layer Context Compression Benchmark",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--eps", "--episodes",
        type=parse_episode_counts,
        default=[10, 50, 100, 200],
        help="Comma-separated episode counts to benchmark (e.g., 10,50,100)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=2,
        help="Number of runs per episode (for cache testing)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1500,
        help="Max token budget for compression",
    )
    parser.add_argument(
        "--book-id",
        type=int,
        default=1,
        help="Book ID for compression context",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for novel generation",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="benchmark_results.json",
        help="Output JSON file path",
    )
    parser.add_argument(
        "--markdown",
        type=str,
        default=None,
        help="Output Markdown report file path (optional)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output",
    )

    args = parser.parse_args()

    # Generate novel at max episode count
    max_ep = max(args.eps)
    if not args.quiet:
        print(f"Generating {max_ep}-episode novel (seed={args.seed})...", file=sys.stderr)

    novel = generate_long_novel(max_ep, seed=args.seed)

    # Run benchmark
    if not args.quiet:
        print(f"Running benchmark at checkpoints: {args.eps}...", file=sys.stderr)

    result = benchmark_novel(
        novel,
        book_id=args.book_id,
        max_tokens=args.max_tokens,
        runs_per_ep=args.runs,
        ep_counts=args.eps,
    )

    # Output results
    if not args.quiet:
        print_checkpoints_report(result["checkpoints"])
        print()
        # Print detailed report for max episode count
        max_cp = max(result["checkpoints"].keys())
        print_report(result["checkpoints"][max_cp], f"Benchmark Report ({max_cp} episodes)")

        # Scaling metrics
        scaling = compute_scaling_metrics(result["checkpoints"])
        if scaling:
            print(f"\nSCALING ANALYSIS:")
            print(f"  Latency per episode: {scaling['latency_per_episode_ms']:.3f} ms/ep")
            print(f"  Memory per episode:  {scaling['memory_per_episode_mb']:.4f} MB/ep")

    # Save JSON
    save_json(result, args.out)

    # Save Markdown if requested
    if args.markdown:
        save_markdown_report(
            result["checkpoints"][max_cp],
            args.markdown,
            title=f"4-Layer Compression Benchmark ({max_cp} episodes)",
            checkpoints=result["checkpoints"],
        )

    if not args.quiet:
        print(f"\nDone. Results saved to {args.out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())