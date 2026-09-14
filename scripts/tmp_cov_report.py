import json

data = json.load(open("coverage.json", encoding="utf-8"))
files = [
    (
        v["summary"]["percent_covered"],
        k,
        v["summary"]["num_statements"],
        v["summary"].get("missing_lines", 0),
    )
    for k, v in data["files"].items()
]
files.sort()
zero = [f for f in files if f[0] == 0]

total_stmts = sum(f[2] for f in files)
zero_stmts = sum(f[2] for f in zero)
print("TOTAL:", round(data["totals"]["percent_covered"], 2))
print(f"ZERO coverage files: {len(zero)} of {len(files)}, stmts {zero_stmts}/{total_stmts}")

# biggest zero-coverage wins
big = sorted(zero, key=lambda f: -f[2])[:60]
print("\n--- largest zero-coverage files (by statements) ---")
for p, k, n, m in big:
    print(f"{p:6.2f}% {n:6d} stmts {k}")

# low coverage (1-50%)
low = [f for f in files if 0 < f[0] < 50]
low_stmts = sum(f[3] for f in low)
print(f"\n--- files with coverage 1-50%: {len(low)} files, missing lines {low_stmts} ---")
low.sort(key=lambda f: -f[3])
for p, k, n, m in low[:40]:
    print(f"{p:6.2f}% {n:6d} stmts {m:6d} missing  {k}")
