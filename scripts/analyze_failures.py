"""一時検証スクリプト: 失敗テストの集計。"""
import re

text = open("output/coverage-round2.log", encoding="utf-8", errors="replace").read()
failed = re.findall(r"^(?:FAILED|ERROR) [^\n]+", text, re.M)
from collections import Counter

files = Counter()
for f in failed:
    parts = f.split()
    if len(parts) > 1:
        path = parts[1].split("::")[0]
        files[path] += 1
for k, v in files.most_common(30):
    print(v, k)
