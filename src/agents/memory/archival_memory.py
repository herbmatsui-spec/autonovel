"""ArchivalMemory adapter wrapping VectorStore, GraphStore and EventLogStore."""
from __future__ import annotations

import math
import uuid
from typing import Any, Dict, List, Optional, Tuple

from src.agents.memory.interfaces import BaseArchivalMemory, MemoryEntry
from src.pipeline.emotional_residue import EmotionalVector, EmotionType
from src.stores.vector_store import VectorStore


class ArchivalMemory(BaseArchivalMemory):
    """長期記憶（外部記憶）を管理するアダプター"""

    def __init__(
        self,
        vector_store: VectorStore,
        graph_store: Optional[Any] = None,
        event_log_store: Optional[Any] = None,
    ):
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.event_log_store = event_log_store
        self._entries: Dict[str, MemoryEntry] = {}

    def insert(self, entry: MemoryEntry) -> None:
        """エントリをアーカイブに挿入"""
        self._entries[entry.id] = entry

    def delete(self, entry_id: str) -> bool:
        """エントリを削除"""
        if entry_id in self._entries:
            del self._entries[entry_id]
            return True
        return False

    def search(self, query: str, k: int = 5) -> List[MemoryEntry]:
        """クエリに基づいて関連エントリを類似度検索（キーワード・簡易類似度）"""
        q_tokens = set(query.lower().split())
        scored: List[Tuple[float, MemoryEntry]] = []

        for entry in self._entries.values():
            c_tokens = set(entry.content.lower().split())
            overlap = len(q_tokens & c_tokens)
            score = overlap / max(1, len(q_tokens))
            if query.lower() in entry.content.lower():
                score += 1.0
            scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for score, entry in scored[:k] if score > 0] or list(self._entries.values())[:k]

    def search_emotional_scenes(self, query: str, k: int = 5) -> List[MemoryEntry]:
        """感情シーンの類似検索"""
        return self.search(query, k=k)

    def insert_emotional_summary(
        self,
        episode: int,
        summary: str,
        vector: Optional[EmotionalVector] = None,
    ) -> MemoryEntry:
        """エピソードの感情要約とベクトルを保存"""
        entry_id = f"ep{episode}_summary_{uuid.uuid4().hex[:6]}"
        metadata: Dict[str, Any] = {"episode": episode, "type": "emotional_summary"}
        if vector:
            metadata["vector"] = vector.to_dict()

        entry = MemoryEntry(
            id=entry_id,
            content=summary,
            metadata=metadata,
        )
        self.insert(entry)

        # VectorStore の archival ネームスペースにも保存
        if vector:
            self.vector_store.upsert("archival", f"ep{episode}:summary", vector)

        return entry

    def trace_emotional_cause(
        self,
        source: str,
        target: str,
        emotion: str,
    ) -> List[Dict[str, Any]]:
        """感情因果パスの探索（GraphStore または保存済み原因ログから追跡）"""
        if self.graph_store and hasattr(self.graph_store, "trace_cause"):
            return self.graph_store.trace_cause(source, target, emotion)

        causes = []
        for entry in self._entries.values():
            meta = entry.metadata
            if meta.get("type") == "emotional_summary" and "vector" in meta:
                v_dict = meta["vector"]
                signals = v_dict.get("signals", {})
                for k_str, val in signals.items():
                    # k_str match
                    if source in k_str and target in k_str and emotion in k_str:
                        causes.append({
                            "episode": meta.get("episode"),
                            "cause": entry.content,
                            "value": val,
                        })
        return causes

    def get_emotional_history(
        self,
        pair: Tuple[str, str],
        from_ep: int = 1,
        to_ep: int = 50,
    ) -> List[Dict[str, Any]]:
        """指定ペアの過去エピソードにわたる感情履歴を取得"""
        if self.event_log_store and hasattr(self.event_log_store, "get_history"):
            return self.event_log_store.get_history(pair, from_ep, to_ep)

        history = []
        src, tgt = pair
        for ep in range(from_ep, to_ep + 1):
            vec = self.vector_store.get_latest("fused", (src, tgt)) or self.vector_store.get_latest("annotation", (src, tgt))
            if vec:
                emotions = vec.get_pair_emotions(src, tgt)
                if emotions:
                    history.append({
                        "episode": ep,
                        "emotions": {emo.value if hasattr(emo, "value") else str(emo): val for emo, val in emotions.items()},
                    })
        return history


__all__ = ["ArchivalMemory"]
