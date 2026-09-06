#!/usr/bin/env python3
"""Weekly A/B Test Analysis Script.

Analyzes audit metrics to detect statistically significant differences
between weight variants. Run via cron weekly.

Usage:
    python scripts/analyze_ab_test.py --since-days 7 --min-samples 30
    python scripts/analyze_ab_test.py --since-days 7 --output-json results.json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.weight_variants import WEIGHT_VARIANTS, SPECIALIST_NAMES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Statistical thresholds
MIN_SAMPLES_PER_VARIANT = 30
P_VALUE_THRESHOLD = 0.05
EFFECT_SIZE_THRESHOLD = 0.2  # Cohen's d / Cliff's delta minimum
MIN_IMPROVEMENT_PCT = 1.0    # Minimum 1% relative improvement


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    """Compute Cliff's delta (non-parametric effect size).

    Returns value in [-1, 1]:
    - 1: all x > y
    - 0: no difference
    - -1: all x < y

    Thresholds (Romano et al. 2006):
    - |d| < 0.147: negligible
    - 0.147 <= |d| < 0.33: small
    - 0.33 <= |d| < 0.474: medium
    - |d| >= 0.474: large
    """
    if len(x) == 0 or len(y) == 0:
        return 0.0

    # Vectorized computation
    greater = np.sum(x[:, None] > y)
    less = np.sum(x[:, None] < y)
    total = len(x) * len(y)
    return (greater - less) / total


def cohens_d(x: np.ndarray, y: np.ndarray) -> float:
    """Compute Cohen's d (parametric effect size)."""
    if len(x) < 2 or len(y) < 2:
        return 0.0

    nx, ny = len(x), len(y)
    dof = nx + ny - 2
    pooled_std = np.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / dof)

    if pooled_std == 0:
        return 0.0

    return (np.mean(x) - np.mean(y)) / pooled_std


def welch_t_test(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Welch's t-test (unequal variance).

    Returns (t_statistic, p_value)
    """
    if len(x) < 2 or len(y) < 2:
        return 0.0, 1.0

    t_stat, p_val = stats.ttest_ind(x, y, equal_var=False)
    return float(t_stat), float(p_val)


def mannwhitney_u_test(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Mann-Whitney U test (non-parametric).

    Returns (u_statistic, p_value)
    """
    if len(x) == 0 or len(y) == 0:
        return 0.0, 1.0

    try:
        u_stat, p_val = stats.mannwhitneyu(x, y, alternative="two-sided")
        return float(u_stat), float(p_val)
    except Exception:
        return 0.0, 1.0


def analyze_variant_pair(
    control_scores: np.ndarray,
    treatment_scores: np.ndarray,
    control_name: str,
    treatment_name: str,
    metric_name: str = "overall_score",
) -> dict[str, Any]:
    """Analyze a control vs treatment variant pair.

    Returns analysis result dict.
    """
    result = {
        "metric": metric_name,
        "control_variant": control_name,
        "treatment_variant": treatment_name,
        "control_n": int(len(control_scores)),
        "treatment_n": int(len(treatment_scores)),
        "control_mean": float(np.mean(control_scores)) if len(control_scores) > 0 else 0.0,
        "treatment_mean": float(np.mean(treatment_scores)) if len(treatment_scores) > 0 else 0.0,
        "control_median": float(np.median(control_scores)) if len(control_scores) > 0 else 0.0,
        "treatment_median": float(np.median(treatment_scores)) if len(treatment_scores) > 0 else 0.0,
        "control_std": float(np.std(control_scores, ddof=1)) if len(control_scores) > 1 else 0.0,
        "treatment_std": float(np.std(treatment_scores, ddof=1)) if len(treatment_scores) > 1 else 0.0,
    }

    # Skip if insufficient samples
    if len(control_scores) < MIN_SAMPLES_PER_VARIANT or len(treatment_scores) < MIN_SAMPLES_PER_VARIANT:
        result["skipped"] = True
        result["skip_reason"] = f"Insufficient samples (min {MIN_SAMPLES_PER_VARIANT})"
        return result

    # Relative improvement
    if result["control_mean"] > 0:
        result["relative_improvement_pct"] = (
            (result["treatment_mean"] - result["control_mean"]) / result["control_mean"] * 100
        )
    else:
        result["relative_improvement_pct"] = 0.0

    # Statistical tests
    t_stat, p_val = welch_t_test(control_scores, treatment_scores)
    result["welch_t_stat"] = t_stat
    result["welch_p_value"] = p_val

    u_stat, mw_p = mannwhitney_u_test(control_scores, treatment_scores)
    result["mannwhitney_u"] = u_stat
    result["mannwhitney_p_value"] = mw_p

    # Effect sizes
    d = cohens_d(control_scores, treatment_scores)
    delta = cliffs_delta(control_scores, treatment_scores)
    result["cohens_d"] = d
    result["cliffs_delta"] = delta

    # Significance determination
    # Use Welch's t-test p-value as primary, Mann-Whitney as confirmatory
    is_significant = p_val < P_VALUE_THRESHOLD and mw_p < P_VALUE_THRESHOLD
    has_meaningful_effect = abs(delta) >= EFFECT_SIZE_THRESHOLD
    has_min_improvement = result["relative_improvement_pct"] >= MIN_IMPROVEMENT_PCT

    result["statistically_significant"] = bool(is_significant)
    result["meaningful_effect_size"] = bool(has_meaningful_effect)
    result["meets_min_improvement"] = bool(has_min_improvement)

    # Overall recommendation
    if is_significant and has_meaningful_effect and has_min_improvement:
        if result["relative_improvement_pct"] > 0:
            result["recommendation"] = "PROMOTE"
            result["recommendation_reason"] = (
                f"Statistically significant improvement ({result['relative_improvement_pct']:.1f}%), "
                f"p={p_val:.4f}, Cliff's delta={delta:.3f}"
            )
        else:
            result["recommendation"] = "REJECT"
            result["recommendation_reason"] = (
                f"Statistically significant degradation ({result['relative_improvement_pct']:.1f}%), "
                f"p={p_val:.4f}"
            )
    elif is_significant and not has_meaningful_effect:
        result["recommendation"] = "INCONCLUSIVE"
        result["recommendation_reason"] = (
            f"Statistically significant but effect size too small "
            f"(Cliff's delta={delta:.3f} < {EFFECT_SIZE_THRESHOLD})"
        )
    else:
        result["recommendation"] = "NO_DECISION"
        result["recommendation_reason"] = (
            f"Not statistically significant (p={p_val:.4f}) or insufficient improvement"
        )

    return result


def load_mock_data() -> dict[str, list[float]]:
    """Load mock data for testing (replace with real DB query)."""
    np.random.seed(42)

    # Simulate data: control has mean 75, treatments vary
    n_control = 100
    control = np.random.normal(75, 10, n_control)
    control = np.clip(control, 0, 100)

    variants = {
        "default_v1": control,
        "literary_v1": np.random.normal(76, 10, 80).clip(0, 100),
        "literary_v2_consistency_up": np.random.normal(78, 10, 50).clip(0, 100),  # Better
        "entertainment_v1": np.random.normal(74, 12, 60).clip(0, 100),
        "entertainment_v2_hook_up": np.random.normal(73, 12, 45).clip(0, 100),  # Worse
        "mystery_v1": np.random.normal(77, 9, 40).clip(0, 100),
        "mystery_v2_structure_up": np.random.normal(79, 9, 35).clip(0, 100),  # Better
    }

    return variants


def query_database(since_days: int = 7, use_mock: bool = False) -> dict[str, list[float]]:
    """Query audit metrics from database.

    Replace with actual database query.
    Expected schema:
        audit_metrics_mv (materialized view) with columns:
        - weight_variant, genre, phase, overall_score, specialist_scores, evaluated_at

    Returns dict: variant_name -> list of overall_scores
    """
    if use_mock:
        logger.info("Using mock data for analysis")
        return load_mock_data()

    # TODO: Replace with real database query
    # Example SQL:
    # SELECT weight_variant, overall_score
    # FROM audit_metrics_mv
    # WHERE evaluated_at >= NOW() - INTERVAL '7 days'
    # GROUP BY weight_variant

    logger.warning("Using mock data - replace query_database() with real DB query")
    return load_mock_data()


def run_analysis(
    since_days: int = 7,
    min_samples: int = MIN_SAMPLES_PER_VARIANT,
    p_threshold: float = P_VALUE_THRESHOLD,
    effect_threshold: float = EFFECT_SIZE_THRESHOLD,
    min_improvement: float = MIN_IMPROVEMENT_PCT,
    use_mock: bool = False,
) -> dict[str, Any]:
    """Run complete A/B test analysis."""
    global MIN_SAMPLES_PER_VARIANT, P_VALUE_THRESHOLD, EFFECT_SIZE_THRESHOLD, MIN_IMPROVEMENT_PCT
    MIN_SAMPLES_PER_VARIANT = min_samples
    P_VALUE_THRESHOLD = p_threshold
    EFFECT_SIZE_THRESHOLD = effect_threshold
    MIN_IMPROVEMENT_PCT = min_improvement

    logger.info(f"Loading data for last {since_days} days...")
    variant_data = query_database(since_days, use_mock=use_mock)

    if not variant_data:
        logger.error("No data returned from query")
        return {"error": "No data", "analyzed_at": datetime.utcnow().isoformat()}

    logger.info(f"Loaded {len(variant_data)} variants with data")

    # Identify control variants (v1) and treatment variants (v2+)
    control_variants = [v for v in variant_data if v.endswith("_v1")]
    treatment_variants = [v for v in variant_data if not v.endswith("_v1")]

    results = {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "analysis_window_days": since_days,
        "thresholds": {
            "min_samples": min_samples,
            "p_value": p_threshold,
            "effect_size": effect_threshold,
            "min_improvement_pct": min_improvement,
        },
        "variants_analyzed": list(variant_data.keys()),
        "comparisons": [],
        "summary": {
            "total_comparisons": 0,
            "promote": 0,
            "reject": 0,
            "inconclusive": 0,
            "no_decision": 0,
            "skipped": 0,
        },
    }

    # For each treatment, compare against its genre's control
    for treatment in treatment_variants:
        # Extract base genre from treatment name (e.g., "literary_v2_consistency_up" -> "literary")
        parts = treatment.split("_")
        if len(parts) < 2:
            continue
        genre = parts[0]
        control = f"{genre}_v1"

        if control not in variant_data:
            logger.warning(f"No control variant found for {treatment}")
            continue

        control_scores = np.array(variant_data[control])
        treatment_scores = np.array(variant_data[treatment])

        logger.info(f"Analyzing {control} (n={len(control_scores)}) vs {treatment} (n={len(treatment_scores)})")

        comparison = analyze_variant_pair(
            control_scores, treatment_scores, control, treatment
        )
        results["comparisons"].append(comparison)
        results["summary"]["total_comparisons"] += 1

        rec = comparison.get("recommendation", "SKIPPED")
        if rec in results["summary"]:
            results["summary"][rec.lower()] += 1
        else:
            # Handle NO_DECISION case
            if rec == "NO_DECISION":
                results["summary"]["no_decision"] = results["summary"].get("no_decision", 0) + 1
            else:
                results["summary"]["skipped"] += 1

        logger.info(f"  Result: {rec} - {comparison.get('recommendation_reason', '')}")

    return results


def print_results(results: dict[str, Any]) -> None:
    """Print analysis results in human-readable format."""
    print("\n" + "=" * 80)
    print(f"A/B TEST ANALYSIS REPORT")
    print(f"Generated: {results['analyzed_at']}")
    print(f"Window: {results['analysis_window_days']} days")
    print("=" * 80)

    print(f"\nThresholds:")
    for k, v in results["thresholds"].items():
        print(f"  {k}: {v}")

    print(f"\nVariants analyzed: {', '.join(results['variants_analyzed'])}")

    print(f"\nSummary:")
    for k, v in results["summary"].items():
        print(f"  {k}: {v}")

    print(f"\nDetailed Comparisons:")
    print("-" * 80)

    for comp in results["comparisons"]:
        if comp.get("skipped"):
            print(f"\n  {comp['control_variant']} vs {comp['treatment_variant']}: SKIPPED")
            print(f"    Reason: {comp.get('skip_reason', 'Unknown')}")
            continue

        print(f"\n  {comp['control_variant']} (n={comp['control_n']}) "
              f"vs {comp['treatment_variant']} (n={comp['treatment_n']})")
        print(f"    Mean: {comp['control_mean']:.2f} -> {comp['treatment_mean']:.2f} "
              f"({comp['relative_improvement_pct']:+.1f}%)")
        print(f"    Median: {comp['control_median']:.2f} -> {comp['treatment_median']:.2f}")
        print(f"    Welch's t-test: t={comp['welch_t_stat']:.3f}, p={comp['welch_p_value']:.4f}")
        print(f"    Mann-Whitney: U={comp['mannwhitney_u']:.0f}, p={comp['mannwhitney_p_value']:.4f}")
        print(f"    Cohen's d: {comp['cohens_d']:.3f}, Cliff's delta: {comp['cliffs_delta']:.3f}")
        print(f"    Significant: {comp['statistically_significant']}, "
              f"Meaningful effect: {comp['meaningful_effect_size']}, "
              f"Min improvement: {comp['meets_min_improvement']}")
        print(f"    RECOMMENDATION: {comp['recommendation']}")
        print(f"    Reason: {comp['recommendation_reason']}")


def main():
    parser = argparse.ArgumentParser(description="Weekly A/B Test Analysis")
    parser.add_argument("--since-days", type=int, default=7, help="Analysis window in days")
    parser.add_argument("--min-samples", type=int, default=30, help="Minimum samples per variant")
    parser.add_argument("--p-threshold", type=float, default=0.05, help="P-value threshold")
    parser.add_argument("--effect-threshold", type=float, default=0.2, help="Cliff's delta threshold")
    parser.add_argument("--min-improvement", type=float, default=1.0, help="Minimum improvement %")
    parser.add_argument("--output-json", type=str, help="Output results to JSON file")
    parser.add_argument("--mock", action="store_true", help="Use mock data (for testing)")

    args = parser.parse_args()

    try:
        results = run_analysis(
            since_days=args.since_days,
            min_samples=args.min_samples,
            p_threshold=args.p_threshold,
            effect_threshold=args.effect_threshold,
            min_improvement=args.min_improvement,
            use_mock=args.mock,
        )

        print_results(results)

        if args.output_json:
            with open(args.output_json, "w") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {args.output_json}")

        # Exit code based on recommendations
        promote_count = results["summary"].get("promote", 0)
        reject_count = results["summary"].get("reject", 0)

        if promote_count > 0:
            print(f"\n✅ {promote_count} variant(s) recommended for promotion")
            sys.exit(0)
        elif reject_count > 0:
            print(f"\n❌ {reject_count} variant(s) recommended for rejection")
            sys.exit(1)
        else:
            print(f"\n⏸ No clear winners or losers this period")
            sys.exit(0)

    except Exception as e:
        logger.exception("Analysis failed")
        sys.exit(2)


if __name__ == "__main__":
    main()