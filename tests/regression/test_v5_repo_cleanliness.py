"""tests/regression/test_v5_repo_cleanliness.py.

v5系のリリース品質・リポジトリ衛生を担保するため、
1. ルート直下に不要な一時デバッグスクリプトやログファイルが散乱していないこと
2. src 配下で廃止された旧シム（src.agent, age_client等）を直接 import していないこと
3. 初心者向けWebデモが web/demo/ に正規配置されていること
を検証するリグレッション防止テスト。
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def test_no_debug_scripts_in_root():
    """ルートディレクトリに一時デバッグ・検証スクリプトが存在しないこと."""
    forbidden_patterns = [
        "debug_*.py",
        "manual_verification.py",
        "final_verification.py",
        "test_simple.py",
        "fail_*.txt",
        "full_test_result.txt",
    ]
    violations = []
    for pattern in forbidden_patterns:
        for file in ROOT_DIR.glob(pattern):
            if file.is_file():
                violations.append(file.name)

    assert not violations, f"ルートディレクトリに禁止された一時ファイルが存在します: {violations}"


def test_web_demo_exists_in_web_demo():
    """初心者向けHTMLデモが web/demo/ に正規配置されていること."""
    demo_dir = ROOT_DIR / "web" / "demo"
    assert demo_dir.exists(), "web/demo ディレクトリが存在しません"
    assert (demo_dir / "index.html").exists(), "web/demo/index.html が存在しません"
    assert (demo_dir / "script.js").exists(), "web/demo/script.js が存在しません"
    assert (demo_dir / "mock-data.js").exists(), "web/demo/mock-data.js が存在しません"
    assert (demo_dir / "style.css").exists(), "web/demo/style.css が存在しません"


def test_no_deprecated_module_imports_in_src():
    """src 配下の全 Python コードで廃止済みモジュールが直接 import されていないこと."""
    forbidden_modules = {
        "src.agent",  # agents (複数形) を使用すべき
        "src.services.age_client",  # ChromaDB / Relational Memory を使用すべき
    }

    src_dir = ROOT_DIR / "src"
    violations = []

    for py_file in src_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        if alias.name == forbidden or alias.name.startswith(f"{forbidden}."):
                            violations.append(f"{py_file.relative_to(ROOT_DIR)}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in forbidden_modules:
                        if node.module == forbidden or node.module.startswith(f"{forbidden}."):
                            violations.append(f"{py_file.relative_to(ROOT_DIR)}: from {node.module} import ...")

    assert not violations, f"廃止済みモジュールへの依存が検出されました:\n" + "\n".join(violations)


if __name__ == "__main__":
    test_no_debug_scripts_in_root()
    test_web_demo_exists_in_web_demo()
    test_no_deprecated_module_imports_in_src()
    print("ALL REPO CLEANLINESS REGRESSION TESTS PASSED!")
