"""FastAPI アプリに同一 (method, path) が重複登録されていないことを保証する。"""
from __future__ import annotations

from collections import Counter

from src.backend.server import app


def test_no_duplicate_method_path_pairs():
    seen = Counter()
    for route in app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if not methods or not path:
            continue
        for method in methods:
            seen[(method, path)] += 1
    duplicates = [f"{m} {p} x{c}" for (m, p), c in seen.items() if c > 1]
    assert not duplicates, "重複ルート:\n" + "\n".join(duplicates)
