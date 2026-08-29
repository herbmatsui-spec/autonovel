"""tests/unit/test_world_checker.py"""
from src.consistency.checkers.world import WorldChecker
from src.consistency.checkers.base import CheckContext
from src.filesystem_memory.paths import get_workspace_path, ensure_workspace_dirs
from src.filesystem_memory.writer import write_file


def test_world_checker_prohibited_term(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.filesystem_memory.paths.WORKSPACE_ROOT", tmp_path / "ws"
    )
    from src.filesystem_memory.paths import get_workspace_path as gwp

    base = gwp(1, 1)
    ensure_workspace_dirs(base)
    write_file(
        base / "WORLD.md",
        """# 世界観
```json
{"prohibited": ["魔法", "ドラゴン"]}
```
""",
    )
    write_file(base / "memory/chapters/chapter_01.md", "彼は魔法を使った")

    checker = WorldChecker()
    findings = checker.check(CheckContext(book_id=1, branch_id=1))
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert "魔法" in findings[0].description


def test_world_checker_allowed(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.filesystem_memory.paths.WORKSPACE_ROOT", tmp_path / "ws"
    )
    from src.filesystem_memory.paths import get_workspace_path as gwp

    base = gwp(2, 1)
    ensure_workspace_dirs(base)
    write_file(
        base / "WORLD.md",
        """# 世界観
```json
{"prohibited": ["魔法"]}
```
""",
    )
    write_file(base / "memory/chapters/chapter_01.md", "彼は剣で戦った")

    checker = WorldChecker()
    findings = checker.check(CheckContext(book_id=2, branch_id=1))
    assert findings == []


def test_world_checker_no_prohibited(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.filesystem_memory.paths.WORKSPACE_ROOT", tmp_path / "ws"
    )
    from src.filesystem_memory.paths import get_workspace_path as gwp

    base = gwp(3, 1)
    ensure_workspace_dirs(base)
    write_file(base / "WORLD.md", "# 世界観\n設定なし")
    write_file(base / "memory/chapters/chapter_01.md", "適当な内容")

    checker = WorldChecker()
    findings = checker.check(CheckContext(book_id=3, branch_id=1))
    assert findings == []