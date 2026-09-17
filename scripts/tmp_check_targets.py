# -*- coding: utf-8 -*-
import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

d = json.load(open("coverage.json", encoding="utf-8"))
t = d["totals"]
print(f'TOTAL: {round(t["percent_covered"],2)}% covered={t["covered_lines"]}/{t["num_statements"]}')
# キー形式の確認（バックスラッシュ/スラッシュの違い）
keys = list(d["files"].keys())
sample = [k for k in keys if "services" in k][:5]
print("sample keys:", sample)
# 両形式で探す
targets = [
    "src/services/conflict_report_service.py",
    "src\\services\\conflict_report_service.py",
]
for tgt in targets:
    f = d["files"].get(tgt)
    if f:
        s = f["summary"]
        print(f'{tgt}: {round(s["percent_covered"],1)}% ({s["covered_lines"]}/{s["num_statements"]})')
