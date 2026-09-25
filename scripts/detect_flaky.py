#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path

def run_with_reruns(test_path, reruns=3, timeout_per_run=60):
    """指定テストを複数回実行し、結果を返す"""
    results = []
    for i in range(reruns):
        try:
            result = subprocess.run(
                ["pytest", test_path, "-v", "--tb=short", f"--timeout={timeout_per_run}"],
                capture_output=True, text=True,
                timeout=timeout_per_run + 10  # Add a little buffer
            )
            passed = result.returncode == 0
        except subprocess.TimeoutExpired:
            passed = False
            result = None
        except Exception as e:
            passed = False
            result = None
            # For other exceptions, we treat as failed
        results.append({
            "run": i+1,
            "passed": passed,
            "stdout": result.stdout if result else "",
            "stderr": result.stderr if result else f"Exception: {e}"
        })
    return results

def main():
    # fail_now.txt からテストリスト取得
    fail_now_path = Path("fail_now.txt")
    if not fail_now_path.exists():
        print("fail_now.txt not found, exiting")
        return 1
    
    test_targets = []
    with open(fail_now_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Format: full_test_result.txt:FAILED <test_path>::<test_class>::<test_method>
            # or sometimes just the test path
            if ":" in line:
                # Split by colon and take the part after the first colon
                parts = line.split(":", 1)
                if len(parts) == 2:
                    test_spec = parts[1].strip()
                    if test_spec.startswith("FAILED "):
                        test_spec = test_spec[7:]  # remove "FAILED "
                    # Now test_spec might be like "tests/unit/agents/test_erotic_pipeline.py::TestEroticCurve::test_curve_creation"
                    # We need to extract the file path up to the first "::"
                    if "::" in test_spec:
                        test_file = test_spec.split("::")[0]
                        if Path(test_file).exists():
                            test_targets.append(test_file)
                    else:
                        # If no ::, then it's just a test file?
                        if Path(test_spec).exists():
                            test_targets.append(test_spec)
            else:
                # If no colon, assume it's a test file path
                if Path(line).exists():
                    test_targets.append(line)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_targets = []
    for t in test_targets:
        if t not in seen:
            seen.add(t)
            unique_targets.append(t)
    test_targets = unique_targets
    
    # Optionally, skip known problematic tests that always hang
    # List of tests known to cause issues (from previous runs)
    known_problematic = {
        "tests/unit/test_marketing_agent.py",
        # Add more as needed
    }
    # Filter out known problematic tests to avoid hanging the entire script
    original_count = len(test_targets)
    test_targets = [t for t in test_targets if t not in known_problematic]
    if len(test_targets) < original_count:
        print(f"Skipped {original_count - len(test_targets)} known problematic tests to avoid hanging")
    
    if not test_targets:
        print("No valid test targets found in fail_now.txt after filtering")
        return 1
    
    flaky_results = {}
    for test in test_targets:
        print(f"Checking {test} for flakiness...")
        results = run_with_reruns(test)
        passed_count = sum(1 for r in results if r["passed"])
        # Consider a test flaky if it passes at least once but not all times
        if 0 < passed_count < len(results):
            flaky_results[test] = results
        # If all runs failed due to timeout, we don't mark as flaky here (it's consistently failing)
        # If all runs passed, it's stable
    
    output_path = Path("artifacts/flaky_tests.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(flaky_results, f, indent=2, ensure_ascii=False)
    
    print(f"Found {len(flaky_results)} flaky tests")
    if flaky_results:
        print("Flaky tests:")
        for test in flaky_results.keys():
            print(f"  - {test}")
    return 0 if len(flaky_results) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())