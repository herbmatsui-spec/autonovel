"""API endpoints for conflict review and manual resolution."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.stores.conflict_store import ConflictStore

router = APIRouter(prefix="/api/conflicts", tags=["conflicts"])

_conflict_store_instance: Optional[ConflictStore] = None


def get_conflict_store() -> ConflictStore:
    global _conflict_store_instance
    if _conflict_store_instance is None:
        _conflict_store_instance = ConflictStore()
    return _conflict_store_instance


def set_conflict_store(store: ConflictStore) -> None:
    global _conflict_store_instance
    _conflict_store_instance = store


class ResolveConflictRequest(BaseModel):
    resolution: str  # "annotation" | "rule_engine" | "pipeline" | "manual"
    manual_value: Optional[float] = None


@router.get("")
def list_conflicts(episode: Optional[int] = Query(None, description="エピソード番号")):
    """矛盾一覧取得"""
    store = get_conflict_store()
    if episode is not None:
        conflicts = store.get_conflicts_by_episode(episode)
    else:
        conflicts = store.get_all_conflicts()
    return [c.to_dict() for c in conflicts]


@router.get("/{conflict_id}")
def get_conflict(conflict_id: str):
    """矛盾詳細取得"""
    store = get_conflict_store()
    c = store.get_conflict(conflict_id)
    if not c:
        raise HTTPException(status_code=404, detail="Conflict not found")
    res = store.get_resolution(conflict_id)
    c_dict = c.to_dict()
    c_dict["resolution"] = res
    return c_dict


@router.post("/{conflict_id}/resolve")
def resolve_conflict(conflict_id: str, body: ResolveConflictRequest):
    """矛盾の手動解決を保存"""
    store = get_conflict_store()
    valid_resolutions = {"annotation", "rule_engine", "pipeline", "manual"}
    if body.resolution not in valid_resolutions:
        raise HTTPException(status_code=400, detail=f"Invalid resolution. Must be one of {valid_resolutions}")

    if body.resolution == "manual" and body.manual_value is None:
        raise HTTPException(status_code=400, detail="manual_value is required when resolution is 'manual'")

    store.resolve_conflict(
        conflict_id=conflict_id,
        resolution=body.resolution,
        manual_value=body.manual_value,
    )
    return {
        "status": "resolved",
        "conflict_id": conflict_id,
        "resolution": body.resolution,
        "manual_value": body.manual_value,
    }
