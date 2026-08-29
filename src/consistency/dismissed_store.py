"""consistency/dismissed_store.py - 却下キー永続化"""
import json
from pathlib import Path
from typing import Dict

from src.filesystem_memory.paths import get_workspace_path


def _store_path(book_id: int, branch_id: int = 1) -> Path:
    return get_workspace_path(book_id, branch_id) / "dismissed_findings.json"


def add_dismissal(book_id: int, finding_key: str, reason: str, branch_id: int = 1) -> None:
    path = _store_path(book_id, branch_id)
    data = get_all_dismissals(book_id, branch_id)
    data[finding_key] = reason
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_all_dismissals(book_id: int, branch_id: int = 1) -> Dict[str, str]:
    path = _store_path(book_id, branch_id)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
