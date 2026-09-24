"""WorkingMemory implementation managing scene-level frames with archival eviction."""
from __future__ import annotations

from typing import List, Optional

from src.agents.memory.archival_memory import ArchivalMemory
from src.agents.memory.interfaces import BaseWorkingMemory, MemoryEntry, WorkingFrame


class WorkingMemory(BaseWorkingMemory):
    """シーン単位の直近文脈を保持する揮発性作業メモリ"""

    def __init__(
        self,
        max_frames: int = 4,
        archival_memory: Optional[ArchivalMemory] = None,
    ):
        self.max_frames = max_frames
        self.archival_memory = archival_memory
        self._frames: List[WorkingFrame] = []

    def push(self, frame: WorkingFrame) -> None:
        """フレームを追加。最大数を超えた場合、最古のフレームを Archival へ退避"""
        if len(self._frames) >= self.max_frames:
            evicted = self._frames.pop(0)
            self._evict_to_archival(evicted)

        self._frames.append(frame)

    def pop(self) -> Optional[WorkingFrame]:
        """最新フレームを取り出す"""
        return self._frames.pop() if self._frames else None

    def peek(self) -> Optional[WorkingFrame]:
        """最新フレームを参照する"""
        return self._frames[-1] if self._frames else None

    def get_frames(self) -> List[WorkingFrame]:
        """全フレーム一覧取得"""
        return list(self._frames)

    def clear(self) -> None:
        """作業メモリを全消去（エピソード終了時など）"""
        self._frames.clear()

    def _evict_to_archival(self, frame: WorkingFrame) -> None:
        """退避されたフレームを ArchivalMemory に保存"""
        if self.archival_memory is not None:
            summary = (
                f"Scene {frame.scene_id} summary: {frame.context_summary} "
                f"Plot: {', '.join(frame.plot_points)}"
            )
            entry = MemoryEntry(
                id=f"scene_{frame.scene_id}_evicted",
                content=summary,
                metadata={
                    "type": "evicted_working_frame",
                    "scene_id": frame.scene_id,
                    "emotional_beats": frame.emotional_beats,
                },
            )
            self.archival_memory.insert(entry)


__all__ = ["WorkingMemory"]
