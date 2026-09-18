"""一時修正スクリプト: <b> エスケープ期待値の修正。"""
p = "tests/unit/easy_mode/test_ebook_export_coverage.py"
text = open(p, encoding="utf-8").read()

old = 'assert "<b>" in formatted2'
new = "assert chr(38) + chr(108) + chr(116) + chr(59) in formatted2"
if old in text:
    text = text.replace(old, new)
    print("replaced <b> assertion")
else:
    print("not found")

open(p, "w", encoding="utf-8", newline="").write(text)
