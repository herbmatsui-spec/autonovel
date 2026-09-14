import json

data = json.load(open("coverage.json", encoding="utf-8"))
files = [
    (v["summary"]["percent_covered"], k, v["summary"]["num_statements"], v["summary"].get("missing_lines", 0))
    for k, v in data["files"].items()
]
zero = [f for f in files if f[0] == 0]
zero.sort(key=lambda f: -f[2])
print("TOTAL:", round(data["totals"]["percent_covered"], 2))
print("files:", len(files), " zero-cov:", len(zero))
print("\n--- top 50 zero-coverage (after omit) ---")
for p, k, n, m in zero[:50]:
    print(f"{p:6.2f}% {n:6d} stmts {m:6d} missing  {k}")

# next: low coverage but with many statements
low = [f for f in files if 0 < f[0] < 40]
low.sort(key=lambda f: -f[3])
print(f"\n--- top 30 low-coverage (<40%) by missing lines ---")
for p, k, n, m in low[:30]:
    print(f"{p:6.2f}% {n:6d} stmts {m:6d} missing  {k}")
