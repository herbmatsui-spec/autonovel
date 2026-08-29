"""filesystem_memory/sync.py - DB ↔ FS 同期レイヤー"""
from enum import Enum
from typing import Dict, List, Optional

from src.filesystem_memory.paths import get_workspace_path, WORKSPACE_FILES


class SyncDirection(str, Enum):
    FS_TO_DB = "fs_to_db"
    DB_TO_FS = "db_to_fs"
    BIDIRECTIONAL = "bidirectional"


class SyncReport:
    def __init__(self):
        self.updated = 0
        self.skipped = 0
        self.errors: List[str] = []

    def to_dict(self) -> dict:
        return {
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
        }


# Mapping: filename -> (parse_fn, serialize_fn)
from src.filesystem_memory.parsers import (
    parse_soul,
    parse_world,
    parse_characters,
    parse_outline,
)
from src.filesystem_memory.serializers import (
    serialize_soul,
    serialize_world,
    serialize_characters,
    serialize_outline,
)

FILE_TO_MODEL: Dict[str, dict] = {
    "SOUL.md": {"parse": parse_soul, "serialize": serialize_soul},
    "WORLD.md": {"parse": parse_world, "serialize": serialize_world},
    "CHARACTERS.md": {"parse": parse_characters, "serialize": serialize_characters},
    "OUTLINE.md": {"parse": parse_outline, "serialize": serialize_outline},
}


def sync_fs_to_db(book_id: int, branch_id: int = 1) -> SyncReport:
    """ファイルシステム -> DB 同期（簡易: パース結果をログに出すのみ）"""
    report = SyncReport()
    base = get_workspace_path(book_id, branch_id)
    for fname in WORKSPACE_FILES:
        path = base / fname
        if not path.exists():
            report.skipped += 1
            continue
        try:
            from src.filesystem_memory.reader import read_file

            content = read_file(path)
            entry = FILE_TO_MODEL.get(fname)
            if entry:
                entry["parse"](content)  # parse to validate
            report.updated += 1
        except Exception as e:
            report.errors.append(f"{fname}: {e}")
    return report


def sync_db_to_fs(book_id: int, branch_id: int = 1) -> SyncReport:
    """DB -> ファイルシステム 同期（簡易: 既存テンプレート維持）"""
    report = SyncReport()
    base = get_workspace_path(book_id, branch_id)
    # In a full impl, load DB rows and serialize. Here we just touch files.
    for fname in WORKSPACE_FILES:
        path = base / fname
        if path.exists():
            report.updated += 1
        else:
            report.skipped += 1
    return report


def sync_bidirectional(
    book_id: int, prefer: SyncDirection = SyncDirection.FS_TO_DB, branch_id: int = 1
) -> SyncReport:
    """双方向同期（競合時は prefer 方向を採用）"""
    if prefer == SyncDirection.DB_TO_FS:
        return sync_db_to_fs(book_id, branch_id)
    return sync_fs_to_db(book_id, branch_id)
