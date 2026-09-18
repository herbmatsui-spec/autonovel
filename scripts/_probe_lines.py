"""一時検証スクリプト: 問題行の表示と置換。"""
p = "tests/unit/easy_mode/test_ebook_export_coverage.py"
lines = open(p, encoding="utf-8").read().splitlines(keepends=True)
print("line 106:", repr(lines[105]))
print("line 144:", repr(lines[143]))
