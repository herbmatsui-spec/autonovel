"""Print coverage summary and 80% gap analysis from coverage.json."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

COV = Path(__file__).resolve().parents[1] / "coverage.json"

if not COV.exists():
    print("no coverage.json")
    sys.exit(1)

with open(COV, encoding="utf-8") as f:
    data = json.load(f)

t = data["totals"]
print("TOTAL: %.2f%%  stmts=%d  missing=%d" % (t["percent_covered"], t["num_statements"], t["missing_lines"]))

files = data["files"]
rows = []
for path, info in files.items():
    s = info["summary"]
    rows.append((s["percent_covered"], path, s["num_statements"], s.get("missing_lines", 0)))

rows.sort()
print("--- lowest coverage files (stmts >= 30, cov < 60%) ---")
for pct, path, ns, miss in rows:
    if ns >= 30 and pct < 60:
        print("%6.2f%%  %5d stmts  %5d miss  %s" % (pct, ns, miss, path))

# How many statements need covering for 80%
target = 0.80
covered = t["num_statements"] - t["missing_lines"]
needed = (t["num_statements"] * target) - covered
print("--- gap analysis ---")
print("need to cover ~%d more statements for 80%%" % max(0, int(needed)))
