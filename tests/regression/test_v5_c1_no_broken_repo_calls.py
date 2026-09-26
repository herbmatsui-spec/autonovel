"""存在しないリポジトリメソッド呼び出しの静的検出。

検出するパターン:
  - `.books.get_by_id(` などの、存在しないメソッドの呼び出し
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "src"

FORBIDDEN = [
    re.compile(r"\.books\.get_by_id\("),
    re.compile(r"\.chapters\.get_by_id\("),
    re.compile(r"\.plots\.get_by_id\("),
    re.compile(r"\.characters\.get_by_id\("),
    re.compile(r"\.branches\.get_by_id\("),
]

# domain / infrastructure リポジトリの get_by_id は正規実装なので対象外にする。
ALLOW_PREFIXES = (
    "src/domain/",
    "src/infrastructure/repositories/",
    "src/application/",
)


def test_no_forbidden_repository_calls():
    offenders: list[str] = []
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel.startswith(ALLOW_PREFIXES):
            continue
        for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            for pattern in FORBIDDEN:
                if pattern.search(line):
                    offenders.append(f"{rel}:{i}: {line.strip()}")
    assert not offenders, "存在しないリポジトリメソッドの呼び出しを検出:\n" + "\n".join(offenders)
