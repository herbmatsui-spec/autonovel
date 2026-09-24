#!/usr/bin/env python3
import json
import subprocess
import time
import sys
from pathlib import Path

def main():
    start = time.time()
    result = subprocess.run(
        ["pytest", "--tb=no", "-q"],  # 出力最小化で正確計測
        capture_output=True, text=True
    )
    end = time.time()
    
    duration = end - start
    passed = result.returncode == 0
    
    data = {
        "total_duration": duration,
        "passed": passed,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "target_met": duration <= 60.0
    }
    
    output_path = Path("artifacts/test_duration.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Test duration: {duration:.2f}s ({'PASS' if data['target_met'] else 'FAIL'} target)")
    return 0 if data['target_met'] else 1

if __name__ == "__main__":
    sys.exit(main())