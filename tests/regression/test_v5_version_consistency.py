"""tests/regression/test_v5_version_consistency.py.

v5系のリリース整合性を担保するため、全設定ファイル・主要コードエントリポイントにおける
バージョン番号が寸分違わず一致していることを検証するリグレッション防止テスト。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
import tomllib
import pytest
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def test_pyproject_toml_version():
    """pyproject.toml のバージョンが 5.2.0 であること."""
    pyproject_path = ROOT_DIR / "pyproject.toml"
    assert pyproject_path.exists(), "pyproject.toml が存在しません"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    version = data.get("project", {}).get("version")
    assert version == "5.2.0", f"pyproject.toml version は 5.2.0 であるべきですが {version} です"


def test_frontend_package_json_version():
    """frontend/package.json のバージョンが 5.2.0 であること."""
    package_json_path = ROOT_DIR / "frontend" / "package.json"
    assert package_json_path.exists(), "frontend/package.json が存在しません"
    with open(package_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    version = data.get("version")
    assert version == "5.2.0", f"package.json version は 5.2.0 であるべきですが {version} です"


def test_cli_version():
    """src/cli/main.py の __version__ が 5.2.0 であること."""
    from src.cli.main import __version__
    assert __version__ == "5.2.0", f"src.cli.main.__version__ は 5.2.0 であるべきですが {__version__} です"


def test_backend_init_version():
    """src/backend/__init__.py の __version__ が 5.2.0 であること."""
    import src.backend
    version = getattr(src.backend, "__version__", None)
    assert version == "5.2.0", f"src.backend.__version__ は 5.2.0 であるべきですが {version} です"


def test_readme_version_matches():
    """README.md のバージョンバッジが 5.2.0 を指していること."""
    readme_path = ROOT_DIR / "README.md"
    assert readme_path.exists(), "README.md が存在しません"
    content = readme_path.read_text(encoding="utf-8")
    assert "version-5.2.0-brightgreen" in content, "README.md のバージョンバッジが 5.2.0 ではありません"
    assert "v5.2.0" in content, "README.md に v5.2.0 の記述が含まれていません"


if __name__ == "__main__":
    test_pyproject_toml_version()
    test_frontend_package_json_version()
    test_cli_version()
    test_backend_init_version()
    test_readme_version_matches()
    print("ALL VERSION CONSISTENCY TESTS PASSED! (v5.2.0)")
