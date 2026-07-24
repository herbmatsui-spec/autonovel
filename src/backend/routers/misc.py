from fastapi import APIRouter, HTTPException
from typing import Optional
import json
from src.core.container import AppContainer as Container
from src.backend.database import UnitOfWork

router = APIRouter(tags=["misc"])

@router.get("/api/books/{book_id}/narrative_metrics", deprecated=True, tags=["metrics"])
async def get_narrative_metrics(book_id: int, branch_id: int = 1, ep_num: Optional[int] = None):
    """[非推奨] 新path版 /api/narrative_metrics/{book_id}/{branch_id} を使用してください。"""
    try:
        from src.backend.database.repositories.narrative_metrics_repo import NarrativeMetricRepository
        async with Container.db().get_session() as session:
            repo = NarrativeMetricRepository(session)
            if ep_num is not None:
                trends = await repo.get_trend_metrics(book_id=book_id, branch_id=branch_id)
                data = [t for t in trends if t.get("ep_num") == ep_num]
            else:
                data = await repo.get_trend_metrics(book_id=book_id, branch_id=branch_id)
            return {"book_id": book_id, "branch_id": branch_id, "metrics": data}
    except Exception as e:
        from src.core.exceptions import AppError
        raise AppError(f"ナラティブメトリクスの取得に失敗: {e}", original=e)

@router.get("/api/bibles/{book_id}")
async def get_bible(book_id: int):
    async with UnitOfWork(Container.db()) as uow:
        b = await uow.bible.get_latest_bible(book_id)
    if not b:
        return {}
    return {
        "id": b.id,
        "book_id": b.book_id,
        "settings": json.loads(b.settings or "{}") if isinstance(b.settings, str) else b.settings,
        "revealed": json.loads(b.revealed or "{}") if isinstance(b.revealed, str) else b.revealed,
        "version": b.version
    }

@router.get("/api/optimization_history/{book_id}")
async def get_opt_history(book_id: int):
    async with UnitOfWork(Container.db()) as uow:
        history = await uow.misc.get_optimization_history(book_id)
    return [
        {
            "id": h.id,
            "report_json": json.loads(h.report_json) if isinstance(h.report_json, str) else h.report_json,
            "created_at": h.created_at
        }
        for h in history
    ]

@router.get("/api/narrative_metrics/{book_id}/{branch_id}")
async def get_narrative_metrics_trend(book_id: int, branch_id: int):
    """
    書籍およびブランチごとの指標推移を取得する。
    """
    async with UnitOfWork(Container.db()) as uow:
        metrics = await uow.narrative_metrics.get_trend_metrics(book_id, branch_id)
        return metrics

@router.get("/api/config/planning_options")
async def get_planning_options():
    """
    フロントエンド向けの企画立案用オプション（ジャンル、アーキタイプ、文体など）を返す。
    """
    from config.archetypes_new import EASY_GENRES, STORY_ARCHETYPES
    from config.styles import STYLE_DEFINITIONS
    from config.constants import PLANNING_PRESETS
    
    # STYLE_DEFINITIONSから必要な部分のみ抽出
    styles = {k: {"name": v.get("name", k), "description": v.get("instruction", "")} for k, v in STYLE_DEFINITIONS.items()}
    
    return {
        "easy_genres": EASY_GENRES,
        "story_archetypes": list(STORY_ARCHETYPES.keys()),
        "style_definitions": styles,
        "planning_presets": PLANNING_PRESETS,
    }
