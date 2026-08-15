"""
routers/hooks.py - 章末フック診断 API

既存の episodes ルーターから章文本を取得し、HookDiagnoser で診断・修正案を提供する。
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer
from src.services.hook_diagnoser import HOOK_THRESHOLD, HookDiagnoser

router = APIRouter(prefix="/api/hooks", tags=["hooks"])


class FixRequest(BaseModel):
    api_key: str
    ep_num: int


@router.get("/books/{book_id}/diagnose")
async def diagnose_hooks(book_id: int) -> Dict[str, Any]:
    """作品の全章についてフック強度を診断する。"""
    from src.backend.database.models import Chapter

    async with UnitOfWork(AppContainer.db()) as uow:
        result = await uow.session.execute(
            __import__("sqlalchemy")
            .select(Chapter)
            .where(Chapter.book_id == book_id)
            .order_by(Chapter.ep_num)
        )
        chapters = [
            {"ep_num": c.ep_num, "title": c.title, "content": c.content or ""}
            for c in result.scalars().all()
        ]

    diagnoser = HookDiagnoser()
    scores = await diagnoser.diagnose(chapters)
    weak = [s for s in scores if s["is_weak"]]
    return {
        "threshold": HOOK_THRESHOLD,
        "total": len(scores),
        "weak_count": len(weak),
        "scores": scores,
    }


@router.post("/books/{book_id}/suggest")
async def suggest_hook_fix(book_id: int, req: FixRequest) -> Dict[str, Any]:
    """指定章のフック改善案を生成する。"""
    from sqlalchemy import select

    from src.backend.database.models import Chapter

    async with UnitOfWork(AppContainer.db()) as uow:
        result = await uow.session.execute(
            select(Chapter).where(Chapter.book_id == book_id).where(Chapter.ep_num == req.ep_num)
        )
        chapter = result.scalar_one_or_none()

    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")

    diagnoser = HookDiagnoser()
    suggestion = await diagnoser.generate_hook_fix(
        {"ep_num": chapter.ep_num, "title": chapter.title, "content": chapter.content or ""},
        api_key=req.api_key,
    )
    return {"ep_num": chapter.ep_num, "suggestion": suggestion}


@router.post("/books/{book_id}/episodes/{ep_num}/apply")
async def apply_hook_fix(book_id: int, ep_num: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """生成した修正案を章末に適用する（本文の末尾を置換し、履歴は別途管理）。"""
    new_tail = payload.get("content")
    if not new_tail:
        raise HTTPException(status_code=422, detail="content is required")

    async with UnitOfWork(AppContainer.db()) as uow:
        # branch_id=1 を既定とする（単一ブランチ前提）
        await uow.chapters.update_chapter_content(branch_id=1, ep_num=ep_num, content=new_tail)
    return {"status": "success", "ep_num": ep_num}
