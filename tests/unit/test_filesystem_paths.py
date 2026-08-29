"""tests/unit/test_filesystem_paths.py"""
from pathlib import Path

from src.filesystem_memory.paths import (
    WORKSPACE_ROOT,
    WORKSPACE_FILES,
    get_workspace_path,
    ensure_workspace_dirs,
)


def test_get_workspace_path_returns_expected():
    p = get_workspace_path(1, 1)
    assert p == WORKSPACE_ROOT / "book_1" / "branch_1"


def test_get_workspace_path_default_branch():
    p = get_workspace_path(5)
    assert p == WORKSPACE_ROOT / "book_5" / "branch_1"


def test_ensure_workspace_dirs_creates_all(tmp_path, monkeypatch):
    # Override root to a temp dir for isolation
    monkeypatch.setattr("src.filesystem_memory.paths.WORKSPACE_ROOT", tmp_path / "ws")
    from src.filesystem_memory.paths import get_workspace_path as gwp

    target = gwp(42, 7)
    ensure_workspace_dirs(target)
    assert (target / "SOUL.md").parent.exists()
    assert (target / "memory" / "chapters").is_dir()


def test_ensure_workspace_dirs_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr("src.filesystem_memory.paths.WORKSPACE_ROOT", tmp_path / "ws")
    from src.filesystem_memory.paths import get_workspace_path as gwp

    target = gwp(99, 1)
    ensure_workspace_dirs(target)
    # Running again should not raise
    ensure_workspace_dirs(target)
    assert target.is_dir()
