"""
src/backend/routers/trace.py - 生成実行記録（Trace） API エンドポイント

Provides functions used by tests to record a generation run, list runs,
and produce a reproducibility markdown report.
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from config.container import Container
from src.backend.database.uow import UnitOfWork
from src.services.reproducibility import build_run_record, build_report

router = APIRouter(prefix="/api/trace", tags=["trace"])

# ---------------------------------------------------------------------------
# Request model for recording a run
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    task_type: str = Field(..., description="タスク種別 (writing 等)")
    prompt_version: str = Field(..., description="プロンプト版タグ")
    model_name: str = Field(..., description="使用モデル名")
    params: dict = Field(default_factory=dict, description="モデルパラメータ")
    payload: dict = Field(default_factory=dict, description="入力ペイロード（ハッシュ対象）")
    output_preview: Optional[str] = Field("", description="出力プレビュー (任意)")
    trace_id: str = Field(..., description="Trace ID")
    chapter_ep: Optional[int] = Field(None, description="章エピソード番号（任意）")

# ---------------------------------------------------------------------------
# Helper to acquire a UnitOfWork (Container.db is overridden in tests)
# ---------------------------------------------------------------------------

def _uow() -> UnitOfWork:
    return UnitOfWork(Container.db())

# ---------------------------------------------------------------------------
# API functions – called directly in tests
# ---------------------------------------------------------------------------

@router.post("/record/{book_id}", response_model=dict)
async def record_run(book_id: int, req: RunRequest) -> dict:
    # Build a run record dict and persist via TraceRepository
    record = build_run_record(
        book_id=book_id,
        task_type=req.task_type,
        prompt_version=req.prompt_version,
        model_name=req.model_name,
        params=req.params,
        payload=req.payload,
        output_preview=req.output_preview or "",
        trace_id=req.trace_id,
        chapter_ep=req.chapter_ep,
    )
    async with _uow() as uow:
        run_id = await uow.trace.add(record)
    return {"status": "success", "run_id": run_id, "input_hash": record["input_hash"]}

@router.get("/list/{book_id}", response_model=List[dict])
async def list_runs(book_id: int, chapter_ep: Optional[int] = None) -> List[dict]:
    async with _uow() as uow:
        runs = await uow.trace.list_by_book(book_id, chapter_ep)
        return [await uow.trace.to_dict(r) for r in runs]

@router.get("/report/{book_id}", response_model=dict)
async def reproducibility_report(book_id: int, chapter_ep: Optional[int] = None) -> dict:
    async with _uow() as uow:
        runs = await uow.trace.list_by_book(book_id, chapter_ep)
        runs_dicts = [await uow.trace.to_dict(r) for r in runs]
    return build_report(runs_dicts)
