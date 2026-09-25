"""coverage.json から未カバー行の多いモジュールをレポートする開発用スクリプト。"""
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "coverage.json"
with open(path, encoding="utf-8") as f:
    d = json.load(f)

rows = []
for p, info in d["files"].items():
    s = info["summary"]
    rows.append((s.get("missing_lines", 0), s.get("num_statements", 0), p))
rows.sort(reverse=True)

print("total missing:", sum(r[0] for r in rows))
for miss, ns, p in rows[: int(sys.argv[2]) if len(sys.argv) > 2 else 40]:
    print(f"{miss:5d}/{ns:5d} ({(ns - miss) / ns * 100:5.1f}%) {p}")
