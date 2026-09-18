"""一時検証スクリプト: age_client.py の構文確認。"""
import ast

try:
    ast.parse(open("src/services/age_client.py", encoding="utf-8").read())
    print("SYNTAX OK")
except SyntaxError as e:
    print("SYNTAX ERROR at line", e.lineno, ":", e.msg)
