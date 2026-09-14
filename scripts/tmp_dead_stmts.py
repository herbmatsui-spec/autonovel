import json

lines = open("never_referenced_modules.txt", encoding="utf-8").read().splitlines()
lines = [l.strip() for l in lines if l.strip()]

data = json.load(open("coverage.json", encoding="utf-8"))

# normalize keys (coverage.json uses backslashes on Windows)
def norm(p):
    return p.replace("/", "\\")

total_stmts = 0
total_files = 0
total_cov = 0.0
skipped = []
for p in lines:
    key = norm(p)
    if key in data["files"]:
        s = data["files"][key]["summary"]
        total_stmts += s["num_statements"]
        total_cov += s["num_statements"] - s["missing_lines"]
        total_files += 1
    else:
        skipped.append(p)

print(f"dead modules found in coverage: {total_files}/{len(lines)}, stmts: {total_stmts}, covered: {total_cov}")
print(f"skipped (not in coverage): {len(skipped)}")
for s in skipped:
    print("  SKIP:", s)

totals = data["totals"]
print("\nOverall before omit:", round(totals["percent_covered"], 2))
new_total = totals["num_statements"] - total_stmts
new_cov = totals["covered_lines"] - total_cov
print(f"After omit: total {new_total}, covered {new_cov} -> {round(100*new_cov/new_total,2)}%")
