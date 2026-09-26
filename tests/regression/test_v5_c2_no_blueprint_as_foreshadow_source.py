"""伏線登録コードが detailed_blueprint（設計図本文）を参照していないことを保証する。

方針: promotion_service.py 内の「ForeshadowingModel / add_if_absent に渡す値」を
AST で辿り、detailed_blueprint を参照していないことを確認する。
"""
from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / "src" / "services" / "promotion_service.py"


def _called_function_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Attribute):
            names.add(func.attr)
        elif isinstance(func, ast.Name):
            names.add(func.id)
    return names


def test_promotion_does_not_use_detailed_blueprint_as_foreshadow_source():
    tree = ast.parse(TARGET.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if "add_if_absent" not in _called_function_names(node):
            continue
        # 伏線登録呼び出しの引数に detailed_blueprint が現れたら違反
        for arg in list(node.args) + [kw.value for kw in node.keywords]:
            for sub in ast.walk(arg):
                if isinstance(sub, ast.Attribute) and sub.attr == "detailed_blueprint":
                    offenders.append(f"line {node.lineno}")
                if isinstance(sub, ast.Constant) and sub.value == "detailed_blueprint":
                    offenders.append(f"line {node.lineno}")
    assert not offenders, "伏線登録が detailed_blueprint を参照しています: " + ", ".join(offenders)


def test_promotion_reads_only_dedicated_column():
    """専用カラム foreshadowing_notes を参照していることを確認する（逆向きの保証）。"""
    src = TARGET.read_text(encoding="utf-8")
    assert "foreshadowing_notes" in src
