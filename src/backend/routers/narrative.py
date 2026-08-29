"""
src/backend/routers/narrative.py - NarrativeState ハブ取得 API エンドポイント
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.backend.auth import require_api_key
from src.backend.database import UnitOfWork
from src.backend.response_helpers import api_success
from src.backend.sse_manager import get_sse_manager
from src.core.container import AppContainer
from src.backend.workflows.narrative_state import NarrativeState
from src.schemas.ux_schemas import AffinityData

logger = logging.getLogger(__name__)

from src.backend.router_helpers import workflow_endpoint
from src.backend.task_helpers import create_task as _create_task
from src.backend.utils.id_generator import generate_prefixed_id as generate_task_id

router = APIRouter(prefix="/api/narrative", tags=["narrative"])


class AffinityOverrideRequest(BaseModel):
    character_name: str = Field(..., description="対象キャラクター名")
    affinity_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="好感度 (0-100)")
    trust_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="信頼度 (0-100)")
    dependency_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="依存度 (0-100)")
    wariness_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="警戒度 (0-100)")
    current_mood: Optional[str] = Field(None, description="心理状態 (wary, observation, tsundere, affectionate, deep_love, neutral)")


@router.get("/{book_id}/{branch_id}")
async def get_narrative_hub(book_id: int, branch_id: int = 1) -> Dict[str, Any]:
    """指定した作品・ブランチの NarrativeState ハブ（最新状態）を取得する"""
    try:
        async with UnitOfWork(AppContainer.db()) as uow:
            data = await uow.misc.load_narrative(book_id, branch_id)
        if data is None:
            return {
                "book_id": book_id,
                "branch_id": branch_id,
                "episodes": {},
                "tension_curve": [],
                "affinity_map": {},
                "foreshadow_registry": [],
                "continuity_violations": [],
                "quality_scores": {},
                "erotic_metrics": {},
                "narrative_scores": {},
            }
        return data
    except Exception as e:
        logger.error(f"Failed to load narrative hub for book {book_id}, branch {branch_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"ナラティブ状態の取得に失敗しました: {e}"
        )


@workflow_endpoint("narrative_affinity_override")
@router.post("/{book_id}/{branch_id}/affinity/override")
async def override_affinity(
    book_id: int,
    req: AffinityOverrideRequest,
    branch_id: int = 1,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """読者/作者のリアルタイム介入（HITL）によりキャラクター好感度・心理状態を動的に上書きする"""
    try:
        # Offload processing to background task (inline for testability)
        task_id = generate_task_id("override_affinity")
        # Initialize task state in DB
        await _create_task(task_id, "好感度上書きを開始中...", total_steps=1)
        # Perform the affinity override directly using the UnitOfWork (mockable in tests)
        async with UnitOfWork(AppContainer.db()) as uow:
            raw_data = await uow.misc.load_narrative(book_id, branch_id)
            if raw_data:
                narrative_state = NarrativeState.from_dict(raw_data)
            else:
                narrative_state = NarrativeState(book_id=book_id, branch_id=branch_id)

            cname = req.character_name
            existing = narrative_state.affinity_map.get(cname)
            if not isinstance(existing, AffinityData):
                if isinstance(existing, dict):
                    existing_copy = dict(existing)
                    existing_copy.setdefault("character_name", cname)
                    try:
                        existing = AffinityData(**existing_copy)
                    except (TypeError, ValueError):
                        existing = AffinityData(character_name=cname)
                elif isinstance(existing, (int, float)):
                    existing = AffinityData(character_name=cname, affinity_score=float(existing))
                else:
                    existing = AffinityData(character_name=cname)

            for field in ["affinity_score", "trust_score", "dependency_score", "wariness_score", "current_mood"]:
                val = getattr(req, field)
                if val is not None:
                    setattr(existing, field, val)
            existing.recent_change = 0.0
            narrative_state.affinity_map[cname] = existing
            await uow.misc.save_narrative(book_id, branch_id, narrative_state.to_dict())

        # Broadcast via SSE
        sse = get_sse_manager()
        await sse.broadcast(
            "affinity_overridden",
            {
                "book_id": book_id,
                "branch_id": branch_id,
                "character_name": cname,
                "affinity_data": existing.model_dump(),
                "message": f"{cname} の好感度・心理状態が手動更新されました (好意:{existing.affinity_score}, 状態:{existing.current_mood})",
            },
        )
        # Return immediate success payload
        return {
            "status": "success",
            "character_name": cname,
            "affinity_data": existing.model_dump(),
        }
    except Exception as e:
        logger.error(f"Failed to override affinity for book {book_id}, branch {branch_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"好感度の上書きに失敗しました: {e}",
        )


@router.get("/{book_id}/{branch_id}/foreshadow/sentinel")
async def get_foreshadow_sentinel(
    book_id: int,
    branch_id: int = 1,
    current_ep: int = 1,
    threshold: int = 5,
) -> Dict[str, Any]:
    """未回収伏線の放置状態（センチネル）を診断し、プロット再構成の必要性を判定する"""
    try:
        from novel_50ep.foreshadow_manager import ForeshadowManager
        fm = ForeshadowManager()
        try:
            from src.prototype.foreshadow_adapter import PersistentForeshadowManager
            pfm = PersistentForeshadowManager(csv_path=fm.csv_path, cliffs_path=fm.cliffs_path)
            async with UnitOfWork(AppContainer.db()) as uow:
                db_data = await pfm.load_persistent(book_id, branch_id, repo=uow.misc)
                if db_data:
                    fm.foreshadows = db_data
        except Exception:
            pass

        unresolved = fm.get_unresolved_foreshadows()
        stale = fm.get_stale_foreshadows(current_ep=current_ep, threshold=threshold)

        return {
            "book_id": book_id,
            "branch_id": branch_id,
            "current_ep": current_ep,
            "threshold": threshold,
            "total_unresolved": len(unresolved),
            "stale_count": len(stale),
            "requires_rebuild": len(stale) > 0,
            "stale_foreshadows": [
                {
                    "ep": item.ep if hasattr(item, "ep") else item.get("ep"),
                    "text": item.text if hasattr(item, "text") else item.get("text"),
                    "stale_episodes": current_ep - (item.ep if hasattr(item, "ep") else item.get("ep", 0)),
                }
                for item in stale
            ],
            "unresolved_foreshadows": [
                {
                    "ep": item.ep if hasattr(item, "ep") else item.get("ep"),
                    "text": item.text if hasattr(item, "text") else item.get("text"),
                    "status": item.status if hasattr(item, "status") else item.get("status", "未回収"),
                }
                for item in unresolved
            ],
        }
    except Exception as e:
        logger.error(f"Failed to check foreshadow sentinel for book {book_id}, branch {branch_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"伏線センチネル診断に失敗しました: {e}"
        )


class PlotRebuildRequest(BaseModel):
    current_ep: int = Field(..., ge=1, description="現在の話数（この話数以降のプロットを再構成）")
    target_episodes: Optional[int] = Field(None, ge=1, description="再構成する全話数（デフォルトは10）")
    genre: Optional[str] = Field("異世界ファンタジー", description="ジャンル")
    theme: Optional[str] = Field("英雄譚", description="テーマ")
    user_instructions: Optional[str] = Field("", description="追加指示")


@workflow_endpoint("narrative_plot_rebuild")
@router.post("/{book_id}/{branch_id}/plot/rebuild")
async def rebuild_plot_with_foreshadows(
    book_id: int,
    branch_id: int,
    req: PlotRebuildRequest,
    api_key: str = Depends(require_api_key),
) -> Dict[str, Any]:
    """未回収・放置伏線を最優先回収対象として組み込み、次章以降のプロットを再構成する"""
    try:
        from novel_50ep.foreshadow_manager import ForeshadowManager
        fm = ForeshadowManager()
        try:
            from src.prototype.foreshadow_adapter import PersistentForeshadowManager
            pfm = PersistentForeshadowManager(csv_path=fm.csv_path, cliffs_path=fm.cliffs_path)
            async with UnitOfWork(AppContainer.db()) as uow:
                db_data = await pfm.load_persistent(book_id, branch_id, repo=uow.misc)
                if db_data:
                    fm.foreshadows = db_data
        except Exception:
            pass

        unresolved = fm.get_unresolved_foreshadows()
        stale = fm.get_stale_foreshadows(current_ep=req.current_ep, threshold=3)

        # 放置伏線と未回収伏線を優先順位付け
        foreshadow_list = []
        for s in stale:
            foreshadow_list.append({
                "ep": s.ep if hasattr(s, "ep") else s.get("ep"),
                "text": f"【最優先放置伏線】{s.text if hasattr(s, 'text') else s.get('text')}",
            })
        for u in unresolved:
            if u not in stale:
                foreshadow_list.append({
                    "ep": u.ep if hasattr(u, "ep") else u.get("ep"),
                    "text": u.text if hasattr(u, "text") else u.get("text"),
                })

        from src.backend.workflows.graphs.plot_graph import compile_plot_graph

        app = compile_plot_graph()

        target_eps = req.target_episodes or 10
        extra_inst = req.user_instructions or ""
        if stale:
            extra_inst += f" ※長期未回収となっている伏線（{len(stale)}件）を必ず序盤の話数で回収・進展させてください。"

        initial_state = {
            "book_id": book_id,
            "branch_id": branch_id,
            "genre": req.genre,
            "theme": req.theme,
            "target_episodes": target_eps,
            "user_instructions": extra_inst,
            "unresolved_foreshadows": foreshadow_list,
            "max_iterations": 2,
        }

        result = await app.ainvoke(initial_state)

        # SSE通知
        sse = get_sse_manager()
        await sse.broadcast(
            "plot_rebuilt",
            {
                "book_id": book_id,
                "branch_id": branch_id,
                "current_ep": req.current_ep,
                "plots_count": len(result.get("parsed_plots", [])),
                "resolved_foreshadows_assigned": sum(
                    len(p.get("assigned_foreshadows", []))
                    for p in result.get("parsed_plots", []) if isinstance(p, dict)
                ),
                "message": f"第{req.current_ep}話以降のプロットを伏線回収優先で再構成しました。",
            },
        )

        return api_success(
            {
                "status": "success",
                "book_id": book_id,
                "branch_id": branch_id,
                "current_ep": req.current_ep,
                "parsed_plots": result.get("parsed_plots", []),
                "quality_score": result.get("quality_score", 0.85),
                "is_approved": result.get("is_approved", True),
            },
            "プロットを再構成しました",
        )
    except Exception as e:
        logger.error(f"Failed to rebuild plot for book {book_id}, branch {branch_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"プロット再構成に失敗しました: {e}"
        )

