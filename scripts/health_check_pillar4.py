"""Standalone Health Check Script for Pillar 4: Closed-Loop PDCA & Commercial Quality Integration.

Run via:
    python scripts/health_check_pillar4.py

Verifies 7 critical subsystems:
1. Specialist Anchor Presets (8 specialists)
2. Score Calibration Engine (Bayesian & Sigmoid)
3. Unified 5D BookScore Bridge
4. Actionable Diffs & Directive Generator
5. Closed-Loop PDCA Runner
6. DAG Replanner & Localized Retry Engine
7. Commercial Benchmark Judge
"""

from __future__ import annotations

import sys
import json
import logging
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.services.commercial_benchmarks import CommercialBenchmarkJudge


def run_health_check() -> int:
    print("=" * 70)
    print(" [HEALTH CHECK] Pillar 4: Closed-Loop PDCA & Commercial Quality")
    print("=" * 70)

    all_passed, details = CommercialBenchmarkJudge.run_system_health_check()

    print("\n--- Subsystem Diagnostics ---")
    for check_key, status in sorted(details.items()):
        icon = "[PASS]" if status else "[FAIL]"
        print(f"  {icon} {check_key}")

    print("-" * 70)
    if all_passed:
        print("  RESULT: ALL 7 SUBSYSTEMS OPERATIONAL (100% HEALTHY)")
        print("=" * 70)
        return 0
    else:
        print("  RESULT: HEALTH CHECK FAILED - PLEASE INSPECT FAILED COMPONENTS")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(run_health_check())
