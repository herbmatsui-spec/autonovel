"""MemoryManager integrating Core, Working, and Archival memory tiers."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.agents.memory.archival_memory import ArchivalMemory
from src.agents.memory.core_memory import CoreMemory
from src.agents.memory.interfaces import MemoryEntry, WorkingFrame
from src.agents.memory.working_memory import WorkingMemory
from src.stores.vector_store import InMemoryVectorStore, VectorStore


class MemoryManager:
    """CoreMemory, WorkingMemory, ArchivalMemory の 3層を統合管理するマネージャー"""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        core_memory: Optional[CoreMemory] = None,
        working_memory: Optional[WorkingMemory] = None,
        archival_memory: Optional[ArchivalMemory] = None,
        max_working_frames: int = 4,
    ):
        self.vector_store = vector_store or InMemoryVectorStore()
        self.archival_memory = archival_memory or ArchivalMemory(vector_store=self.vector_store)
        self.working_memory = working_memory or WorkingMemory(
            max_frames=max_working_frames,
            archival_memory=self.archival_memory,
        )
        self.core_memory = core_memory or CoreMemory()

    def get_emotional_context(self, pair: Tuple[str, str]) -> Dict[str, Any]:
        """ペアの感情状態を取得。CoreMemory に存在すれば返し、なければ Archival から検索"""
        pair_key = f"{pair[0]}->{pair[1]}"
        if pair_key in self.core_memory.character_emotions:
            return dict(self.core_memory.character_emotions[pair_key])

        # CoreMemory にない場合は ArchivalMemory から過去の要約・シーンを検索
        entries = self.archival_memory.search_emotional_scenes(f"{pair[0]} {pair[1]}", k=1)
        if entries:
            return {
                "fallback_source": "archival",
                "content": entries[0].content,
                "metadata": entries[0].metadata,
            }

        return {}

    def update_emotion(
        self,
        source: str,
        target: str,
        emotion: str,
        delta: float,
        reason: str = "",
        episode_label: str = "",
    ) -> float:
        """CoreMemory の感情値を更新し、WorkingMemory の現在フレームにもビートを追加"""
        new_val = self.core_memory.update_emotion(
            source=source,
            target=target,
            emotion=emotion,
            delta=delta,
            reason=reason,
            episode_label=episode_label,
        )

        current_frame = self.working_memory.peek()
        if current_frame is not None:
            current_frame.emotional_beats.append({
                "source": source,
                "target": target,
                "emotion": emotion,
                "delta": delta,
                "reason": reason,
                "result_value": new_val,
            })

        return new_val

    def recall_similar(self, query: str, k: int = 5) -> List[MemoryEntry]:
        """ArchivalMemory から関連する類似シーンや要約を想起"""
        return self.archival_memory.search(query, k=k)

    def trace_cause(self, source: str, target: str, emotion: str) -> List[Dict[str, Any]]:
        """感情の原因となった過去のイベントやプロット因果を追跡"""
        return self.archival_memory.trace_emotional_cause(source, target, emotion)

    def compact(self, max_tokens: int = 2000) -> bool:
        """CoreMemory のトークン圧縮を実行"""
        return self.core_memory.compact_if_needed(max_tokens=max_tokens)

    def save_state(self, directory_path: str | Path) -> None:
        """全メモリ状態をディスクに保存"""
        d = Path(directory_path)
        d.mkdir(parents=True, exist_ok=True)
        self.core_memory.save_to_disk(d / "core_memory.json")

    def load_state(self, directory_path: str | Path) -> bool:
        """ディスクからメモリ状態を復元"""
        d = Path(directory_path)
        core_file = d / "core_memory.json"
        if core_file.exists():
            return self.core_memory.load_from_disk(core_file)
        return False


__all__ = ["MemoryManager"]
