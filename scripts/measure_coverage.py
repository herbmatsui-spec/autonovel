#!/usr/bin/env python3
import json
import subprocess
import sys
from datetime import datetime
import os

def main():
    # Check if coverage.json exists, if not run tests to generate it
    if not os.path.exists("coverage.json"):
        print("coverage.json not found, running tests with coverage and JSON report...")
        result = subprocess.run(
            ["pytest", "--cov=src", "--cov-report=json", "--cov-report=term-missing", "--json-report", "--json-report-file=json-report.json", "-q"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Tests failed with exit code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
    else:
        # Use existing coverage.json and generate JSON report if needed
        if not os.path.exists("json-report.json"):
            print("json-report.json not found, running tests with JSON report...")
            result = subprocess.run(
                ["pytest", "--json-report", "--json-report-file=json-report.json", "-q"],
                capture_output=True, text=True
            )
        else:
            # Use existing json-report.json
            result = type('obj', (object,), {'returncode': 0})()  # Mock successful result
    
    # Load coverage data
    with open("coverage.json", encoding="utf-8") as f:
        cov = json.load(f)
    
    # Load test report data if available
    test_baseline = {}
    if os.path.exists("json-report.json"):
        with open("json-report.json", encoding="utf-8") as f:
            test_report = json.load(f)
        
        # Extract test summary
        test_baseline = {
            "total_tests": test_report.get("summary", {}).get("total", 0),
            "passed": test_report.get("summary", {}).get("passed", 0),
            "failed": test_report.get("summary", {}).get("failed", 0),
            "skipped": test_report.get("summary", {}).get("skipped", 0),
            "duration_seconds": test_report.get("duration", 0),
            "failures": [
                {
                    "nodeid": failure.get("nodeid", ""),
                    "message": failure.get("message", "")
                }
                for failure in test_report.get("failures", [])
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        # Save test baseline
        with open("artifacts/test_baseline.json", "w") as f:
            json.dump(test_baseline, f, indent=2, ensure_ascii=False)
        print(f"Test baseline saved: {test_baseline['total_tests']} tests, {test_baseline['passed']} passed, {test_baseline['failed']} failed, {test_baseline['skipped']} skipped")
    else:
        print("Warning: json-report.json not found, skipping test baseline")
    
    # Create coverage baseline
    coverage_baseline = {
        "total_coverage": cov["totals"]["percent_covered"],
        "files": {k: v["summary"]["percent_covered"] for k, v in cov["files"].items()},
        "timestamp": datetime.now().isoformat(),
        "pytest_exit_code": getattr(result, 'returncode', 0)
    }
    
    with open("artifacts/coverage_baseline.json", "w") as f:
        json.dump(coverage_baseline, f, indent=2, ensure_ascii=False)
    
    print(f"Baseline coverage: {coverage_baseline['total_coverage']:.1f}%")
    return 0 if getattr(result, 'returncode', 0) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())