import json
from collections import defaultdict
import os

with open("coverage.json", "r", encoding="utf-8") as f:
    data = json.load(f)

files = data.get("files", {})
dir_stats = defaultdict(lambda: {"statements": 0, "covered": 0, "missing": 0, "files": 0, "file_list": []})

for path, info in files.items():
    norm_path = path.replace("\\", "/")
    if "src/" in norm_path:
        rel = norm_path.split("src/", 1)[1]
        top_dir = rel.split("/")[0] if "/" in rel else "root"
        sub_dir = "/".join(rel.split("/")[:2]) if "/" in rel else rel
    else:
        top_dir = "other"
        rel = norm_path
        sub_dir = rel

    summary = info.get("summary", {})
    stmts = summary.get("num_statements", 0)
    cov = summary.get("covered_lines", 0)
    missing = summary.get("missing_lines", 0)

    dir_stats[top_dir]["statements"] += stmts
    dir_stats[top_dir]["covered"] += cov
    dir_stats[top_dir]["missing"] += missing
    dir_stats[top_dir]["files"] += 1
    dir_stats[top_dir]["file_list"].append((rel, stmts, cov, missing))

print("=== ディレクトリ別カバレッジサマリー ===")
print(f"{'Directory':<20} | {'Files':>5} | {'Stmts':>7} | {'Covered':>7} | {'Missing':>7} | {'Coverage':>8}")
print("-" * 65)

total_stmts = 0
total_cov = 0
total_missing = 0

for d, s in sorted(dir_stats.items(), key=lambda x: x[1]["statements"], reverse=True):
    pct = (s["covered"] / s["statements"] * 100) if s["statements"] > 0 else 0
    total_stmts += s["statements"]
    total_cov += s["covered"]
    total_missing += s["missing"]
    print(f"{d:<20} | {s['files']:>5} | {s['statements']:>7} | {s['covered']:>7} | {s['missing']:>7} | {pct:>7.1f}%")

print("-" * 65)
tot_pct = (total_cov / total_stmts * 100) if total_stmts > 0 else 0
print(f"{'TOTAL':<20} | {'-':>5} | {total_stmts:>7} | {total_cov:>7} | {total_missing:>7} | {tot_pct:>7.1f}%")

print("\n=== ステートメント数順 未カバー行が多いファイル TOP 30 ===")
all_files = []
for d, s in dir_stats.items():
    for fpath, stmts, cov, missing in s["file_list"]:
        pct = (cov / stmts * 100) if stmts > 0 else 0
        all_files.append((fpath, stmts, cov, missing, pct))

all_files.sort(key=lambda x: x[3], reverse=True) # sort by missing
for fpath, stmts, cov, missing, pct in all_files[:30]:
    print(f"{missing:>5} missing | {stmts:>5} total | {pct:>5.1f}% cov | src/{fpath}")
