"""一時検証スクリプト: episode_writer.py の構文確認。"""
import ast

try:
    ast.parse(open("src/agents/writing/episode_writer.py", encoding="utf-8").read())
    print("SYNTAX OK")
except SyntaxError as e:
    print("SYNTAX ERROR at line", e.lineno, e.msg)
