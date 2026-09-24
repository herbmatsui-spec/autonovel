"""Compaction policy for CoreMemory eviction and summarization."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.agents.memory.archival_memory import ArchivalMemory
from src.agents.memory.core_memory import CoreMemory
from src.agents.memory.interfaces import MemoryEntry


class CompactionPolicy:
    """CoreMemory をトークン上限内に収めるための圧縮・退避ポリシー"""

    def __init__(
        self,
        max_tokens: int = 2000,
        stale_episode_threshold: int = 5,
    ):
        self.max_tokens = max_tokens
        self.stale_episode_threshold = stale_episode_threshold

    def compact(
        self,
        core_memory: CoreMemory,
        current_episode: int,
        archival_memory: Optional[ArchivalMemory] = None,
    ) -> Dict[str, Any]:
        """CoreMemory 内の古い感情や長大な履歴を圧縮し、必要に応じて ArchivalMemory に退避する"""
        if core_memory.estimate_tokens() <= self.max_tokens:
            return {"compacted": False, "reason": "within_token_budget"}

        evicted_emotions = []
        # 1. 5話以上更新されていない感情を Archival へ退避して Core から削除
        for pair_key, emotions in list(core_memory.character_emotions.items()):
            updated_str = emotions.get("updated", "")
            match = re.search(r'ep(\d+)', updated_str)
            if match:
                up_ep = int(match.group(1))
                if (current_episode - up_ep) >= self.stale_episode_threshold:
                    if archival_memory is not None:
                        entry = MemoryEntry(
                            id=f"stale_emotion_{pair_key}_ep{up_ep}",
                            content=f"Archived historical emotion for {pair_key} from ep{up_ep}: {emotions}",
                            metadata={"pair": pair_key, "episode": up_ep, "type": "stale_emotion"},
                        )
                        archival_memory.insert(entry)
                    del core_memory.character_emotions[pair_key]
                    evicted_emotions.append(pair_key)

        # 2. relationship_dynamics の trust_trajectory 圧縮（直近10話保持、それ以前は平均値）
        for pair_key, dyn in core_memory.relationship_dynamics.items():
            if isinstance(dyn, dict) and "trust_trajectory" in dyn:
                traj = dyn["trust_trajectory"]
                if len(traj) > 10:
                    older = traj[:-10]
                    dyn["historical_avg_trust"] = round(sum(older) / len(older), 3)
                    dyn["trust_trajectory"] = traj[-10:]

        # 3. active_hooks の整理
        core_memory.compact_if_needed(max_tokens=self.max_tokens)

        return {
            "compacted": True,
            "evicted_emotions": evicted_emotions,
            "estimated_tokens_after": core_memory.estimate_tokens(),
        }


__all__ = ["CompactionPolicy"]
