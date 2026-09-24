"""Agent memory inspection, dump and compaction API endpoints."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException

from src.agents.memory.manager import MemoryManager

router = APIRouter(prefix="/api/agent/memory", tags=["agent_memory"])

_agent_memory_manager: Optional[MemoryManager] = None


def get_agent_memory_manager() -> MemoryManager:
    global _agent_memory_manager
    if _agent_memory_manager is None:
        _agent_memory_manager = MemoryManager()
    return _agent_memory_manager


def set_agent_memory_manager(manager: MemoryManager) -> None:
    global _agent_memory_manager
    _agent_memory_manager = manager


@router.get("/core")
def get_core_memory() -> Dict[str, Any]:
    """CoreMemory の全内容をダンプ"""
    manager = get_agent_memory_manager()
    return manager.core_memory.dump()


@router.get("/working")
def get_working_memory() -> List[Dict[str, Any]]:
    """WorkingMemory のフレームスタックを取得"""
    manager = get_agent_memory_manager()
    frames = manager.working_memory.get_frames()
    return [f.to_dict() for f in frames]


@router.get("/archival/stats")
def get_archival_stats() -> Dict[str, Any]:
    """ArchivalMemory の統計情報取得"""
    manager = get_agent_memory_manager()
    entries = list(manager.archival_memory._entries.values())
    return {
        "total_entries": len(entries),
        "entry_types": list({e.metadata.get("type", "unknown") for e in entries}),
    }


@router.post("/compact")
def force_compact_memory() -> Dict[str, Any]:
    """CoreMemory の強制圧縮を実行"""
    manager = get_agent_memory_manager()
    compacted = manager.compact()
    return {
        "compacted": compacted,
        "tokens_after": manager.core_memory.estimate_tokens(),
    }
