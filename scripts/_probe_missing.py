"""一時検証スクリプト: 指定モジュールの未カバー行を表示。"""
import json
import sys

target = sys.argv[1]
d = json.load(open("output/coverage-round1.json", encoding="utf-8"))
for path, info in d["files"].items():
    p = path.replace("\\", "/")
    if p.endswith(target):
        s = info["summary"]
        miss = s.get("missing_lines", [])
        if isinstance(miss, int):
            miss = info.get("missing_lines", [])
        print(p, "missing:", len(miss) if isinstance(miss, list) else miss)
        print(miss)
        break
