"""Branch memory manager for what-if route branches and memory state comparisons."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.agent.memory.core_memory import CoreMemory


class BranchMemoryManager:
    """IFルートやプロット分岐ごとの CoreMemory を管理するマネージャー"""

    def __init__(self, project_id: str, base_dir: Optional[str | Path] = None):
        self.project_id = project_id
        self.base_dir = Path(base_dir) if base_dir else Path("memory") / project_id
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_branch_path(self, branch_name: str) -> Path:
        return self.base_dir / branch_name / "core_memory.json"

    def load_branch(self, branch_name: str) -> CoreMemory:
        """ブランチの CoreMemory をロード"""
        path = self._get_branch_path(branch_name)
        mem = CoreMemory()
        if path.exists():
            mem.load_from_disk(path)
        return mem

    def save_branch(self, branch_name: str, core_memory: CoreMemory) -> Path:
        """ブランチの CoreMemory を保存"""
        path = self._get_branch_path(branch_name)
        return core_memory.save_to_disk(path)

    def fork_branch(self, base_branch: str, new_branch: str) -> CoreMemory:
        """既存ブランチから新規IFブランチを作成（ディープコピー）"""
        base_mem = self.load_branch(base_branch)
        new_data = copy.deepcopy(base_mem.dump())
        forked_mem = CoreMemory(new_data)
        self.save_branch(new_branch, forked_mem)
        return forked_mem

    def compare_branches(self, branch1: str, branch2: str) -> Dict[str, Any]:
        """2つのブランチ間の感情差分を比較"""
        mem1 = self.load_branch(branch1)
        mem2 = self.load_branch(branch2)

        diffs = {}
        all_pairs = set(mem1.character_emotions.keys()) | set(mem2.character_emotions.keys())
        for pair in all_pairs:
            emo1 = mem1.character_emotions.get(pair, {})
            emo2 = mem2.character_emotions.get(pair, {})
            if emo1 != emo2:
                diffs[pair] = {
                    branch1: emo1,
                    branch2: emo2,
                }

        return {
            "branch1": branch1,
            "branch2": branch2,
            "differences_count": len(diffs),
            "differences": diffs,
        }

    def merge_branch(self, source_branch: str, target_branch: str, strategy: str = "auto") -> CoreMemory:
        """ブランチをマージ（auto: ソース側で上書きマージ）"""
        src_mem = self.load_branch(source_branch)
        tgt_mem = self.load_branch(target_branch)

        # 感情の統合
        for pair, emos in src_mem.character_emotions.items():
            tgt_emos = tgt_mem.character_emotions.setdefault(pair, {})
            tgt_emos.update(emos)

        # active_hooks の統合
        tgt_mem.active_hooks.extend(src_mem.active_hooks)
        tgt_mem.compact_if_needed()

        self.save_branch(target_branch, tgt_mem)
        return tgt_mem


__all__ = ["BranchMemoryManager"]
