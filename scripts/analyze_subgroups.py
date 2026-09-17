import json
from collections import defaultdict

with open("coverage.json", "r", encoding="utf-8") as f:
    data = json.load(f)

files = data.get("files", {})

# Group by 2nd-level directory or functional domain
groups = defaultdict(lambda: {"stmts": 0, "cov": 0, "missing": 0, "files": []})

for path, info in files.items():
    norm = path.replace("\\", "/")
    if "src/" in norm:
        rel = norm.split("src/", 1)[1]
    else:
        continue
    
    parts = rel.split("/")
    if len(parts) >= 2:
        grp = f"{parts[0]}/{parts[1]}"
    else:
        grp = parts[0]
        
    s = info.get("summary", {})
    stmts = s.get("num_statements", 0)
    cov = s.get("covered_lines", 0)
    missing = s.get("missing_lines", 0)
    pct = (cov / stmts * 100) if stmts > 0 else 0
    
    groups[grp]["stmts"] += stmts
    groups[grp]["cov"] += cov
    groups[grp]["missing"] += missing
    groups[grp]["files"].append((rel, stmts, cov, missing, pct))

sorted_groups = sorted(groups.items(), key=lambda x: x[1]["missing"], reverse=True)

print(f"{'Group':<35} | {'Files':>5} | {'Stmts':>6} | {'Covered':>7} | {'Missing':>7} | {'Cov%':>6}")
print("-" * 75)
for grp, d in sorted_groups[:35]:
    pct = (d["cov"] / d["stmts"] * 100) if d["stmts"] > 0 else 0
    print(f"{grp:<35} | {len(d['files']):>5} | {d['stmts']:>6} | {d['cov']:>7} | {d['missing']:>7} | {pct:>5.1f}%")

