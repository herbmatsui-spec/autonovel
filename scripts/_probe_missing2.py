"""一時検証スクリプト: 複数モジュールの未カバー行を一括表示。"""
import json
import sys

targets = sys.argv[1:]
d = json.load(open("output/coverage-round3.json", encoding="utf-8"))
for path, info in d["files"].items():
    p = path.replace("\\", "/")
    for t in targets:
        if p.endswith(t):
            s = info["summary"]
            miss = info.get("missing_lines", [])
            if isinstance(miss, int):
                miss = []
            print("=== ", p, "missing:", len(miss))
            print(miss[:60])
            break
