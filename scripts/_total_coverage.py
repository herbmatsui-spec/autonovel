import json

with open("coverage.json", encoding="utf-8") as f:
    data = json.load(f)

total = data["totals"]
print(f"TOTAL coverage: {total.get('percent_covered', 0):.2f}%")
print(f"covered lines: {total.get('covered_lines', 0)}")
print(f"num_statements: {total.get('num_statements', 0)}")
print(f"files: {total.get('num_files', 0)}")
