"""Run full test suite with coverage and print summary.

Runs pytest via subprocess so the -p no:timeout flag disables pytest-timeout
(whose thread-based timeout deadlocks with IOCP selectors on Windows).
"""

import io
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

cmd = [
    sys.executable, "-m", "pytest", "tests",
    "--ignore=tests/contract/test_db_schema.py",
    "--ignore=tests/load/test_locustfile.py",
    "--ignore=tests/unit/scripts/test_check_env.py",
    "-m", "not perf",
    "-q",
    "--cov=src",
    "--cov-report=json:coverage.json",
    "--cov-report=term",
    "-p", "no:timeout",
    "-o", "addopts=",
]

print("Running:", " ".join(cmd[:6]), "...")
proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5400)

log_path = ROOT / "output" / "full_cov_run.log"
log_path.write_text((proc.stdout or "") + "\n=====STDERR=====\n" + (proc.stderr or ""), encoding="utf-8")

# Print summary lines
for line in (proc.stdout or "").splitlines():
    low = line.lower()
    if "passed" in low or "failed" in low or "total" in low or "timeout" in low:
        print(line)

print("rc =", proc.returncode)
print("log =", log_path)
