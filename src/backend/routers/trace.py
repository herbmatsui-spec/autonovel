"""
routers/trace.py - 生成ログ・Trace ID 再現性レポート API

GenerationRun の記録・取得・再現性レポート(Markdown)生成を提供する。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.backend.auth import get_current_user
from src.backend.database.models import User
from src.backend.database.uow import UnitOfWork
from src.backend.security.owner_guard import verify_book_ownership
from src.core.container import AppContainer
from src.services.reproducibility import build_report, build_run_record

router = APIRouter(
    prefix="/api/trace",
    tags=["trace"],
    dependencies=[Depends(get_current_user)],
)


class RunRequest(BaseModel):
    task_type: str = "writing"
    prompt_version: str = ""
    model_name: str = ""
    params: dict[str, Any] = {}
    payload: dict[str, Any] = {}
    output_preview: str = ""
    trace_id: str = ""
    chapter_ep: int | None = None


@router.post("/books/{book_id}/runs")
async def record_run(
    book_id: int,
    req: RunRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """生成実行のメタデータを記録する。"""
    async with UnitOfWork(AppContainer.db()) as uow:
        await verify_book_ownership(book_id, current_user, uow)
        record = build_run_record(
            book_id=book_id,
            task_type=req.task_type,
            prompt_version=req.prompt_version,
            model_name=req.model_name,
            params=req.params,
            payload=req.payload,
            output_preview=req.output_preview,
            trace_id=req.trace_id,
            chapter_ep=req.chapter_ep,
        )
        rid = await uow.trace.add(record)
    return {"status": "success", "id": rid, "input_hash": record["input_hash"]}


@router.get("/books/{book_id}/runs")
async def list_runs(
    book_id: int,
    chapter_ep: int | None = Query(None),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """生成実行記録を取得する。"""
    async with UnitOfWork(AppContainer.db()) as uow:
        await verify_book_ownership(book_id, current_user, uow)
        runs = await uow.trace.list_by_book(book_id, chapter_ep)
        return [await uow.trace.to_dict(r) for r in runs]


@router.get("/books/{book_id}/report")
async def reproducibility_report(
    book_id: int,
    chapter_ep: int | None = Query(None),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """再現性レポート（Markdown）を生成する。"""
    async with UnitOfWork(AppContainer.db()) as uow:
        await verify_book_ownership(book_id, current_user, uow)
        runs = await uow.trace.list_by_book(book_id, chapter_ep)
        runs_dict = [await uow.trace.to_dict(r) for r in runs]
    return build_report(runs_dict)
