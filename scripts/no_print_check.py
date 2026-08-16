#!/usr/bin/env python3
"""
本番コードでの print 文検出スクリプト
pre-commit フックから呼び出される
"""
import ast
import sys
from pathlib import Path


def check_file(filepath: Path) -> list[tuple[int, str]]:
    """ファイル内の print 文を検出"""
    violations = []
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            func = node.value.func
            if isinstance(func, ast.Name) and func.id == "print":
                violations.append((node.lineno, filepath.name))

    return violations


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python no_print_check.py <file1> [file2...]")
        return 1

    all_violations = []
    for arg in sys.argv[1:]:
        filepath = Path(arg)
        if not filepath.exists():
            continue
        violations = check_file(filepath)
        all_violations.extend((arg, lineno) for lineno, _ in violations)

    if all_violations:
        for filepath, lineno in all_violations:
            print(f"{filepath}:{lineno}: print statement found in production code")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())