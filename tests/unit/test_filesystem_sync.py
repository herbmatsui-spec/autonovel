"""tests/unit/test_filesystem_sync.py"""
from src.filesystem_memory.sync import (
    SyncDirection,
    sync_fs_to_db,
    sync_db_to_fs,
    sync_bidirectional,
    SyncReport,
)
from src.filesystem_memory.paths import get_workspace_path, ensure_workspace_dirs
from src.filesystem_memory.writer import write_file


def test_sync_fs_to_db_parses(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "src.filesystem_memory.paths.WORKSPACE_ROOT", tmp_path / "ws"
    )
    from src.filesystem_memory.paths import get_workspace_path as gwp

    base = gwp(1, 1)
    ensure_workspace_dirs(base)
    write_file(base / "SOUL.md", "# x\n## 文体ガイド\nfoo\n")
    write_file(base / "WORLD.md", "# w\n```json\n{}\n```\n")
    report = sync_fs_to_db(1, 1)
    assert report.updated >= 2
    assert report.to_dict()["updated"] >= 2


def test_sync_direction_enum():
    assert SyncDirection("fs_to_db") == SyncDirection.FS_TO_DB
    assert SyncDirection("db_to_fs") == SyncDirection.DB_TO_FS
    assert SyncDirection("bidirectional") == SyncDirection.BIDIRECTIONAL


def test_sync_report_to_dict():
    r = SyncReport()
    r.updated = 3
    r.skipped = 1
    d = r.to_dict()
    assert d["updated"] == 3
    assert d["skipped"] == 1
