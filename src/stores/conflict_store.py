"""Conflict store for recording detected and resolved conflicts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.fusion.models import Conflict


class ConflictStore:
    """矛盾レコードの永続化と検索を管理するストア"""

    def __init__(self, file_path: Optional[str | Path] = None):
        self.file_path = Path(file_path) if file_path else Path("logs/conflicts.jsonl")
        self._in_memory: Dict[str, Dict[str, Any]] = {}
        self._resolutions: Dict[str, Dict[str, Any]] = {}
        self._load_if_exists()

    def _load_if_exists(self) -> None:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        data = json.loads(line)
                        cid = data.get("conflict_id")
                        if cid:
                            self._in_memory[cid] = data
            except Exception:
                pass

    def record_conflicts(self, conflicts: List[Conflict], episode: int) -> None:
        """矛盾リストを記録保存する"""
        if not conflicts:
            return

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "a", encoding="utf-8") as f:
            for c in conflicts:
                c_data = c.to_dict()
                c_data["episode"] = episode
                self._in_memory[c.conflict_id] = c_data
                f.write(json.dumps(c_data, ensure_ascii=False) + "\n")

    def get_conflicts_by_episode(self, episode: int) -> List[Conflict]:
        """特定エピソードの矛盾一覧を取得"""
        results = []
        for d in self._in_memory.values():
            if d.get("episode") == episode:
                results.append(Conflict.from_dict(d))
        return results

    def get_all_conflicts(self) -> List[Conflict]:
        """全矛盾一覧を取得"""
        return [Conflict.from_dict(d) for d in self._in_memory.values()]

    def get_conflict(self, conflict_id: str) -> Optional[Conflict]:
        """ID指定で矛盾を取得"""
        d = self._in_memory.get(conflict_id)
        return Conflict.from_dict(d) if d else None

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        manual_value: Optional[float] = None,
    ) -> None:
        """矛盾に対する手動解決を保存"""
        self._resolutions[conflict_id] = {
            "conflict_id": conflict_id,
            "resolution": resolution,
            "manual_value": manual_value,
        }

    def get_resolution(self, conflict_id: str) -> Optional[Dict[str, Any]]:
        """手動解決記録を取得"""
        return self._resolutions.get(conflict_id)


__all__ = ["ConflictStore"]
