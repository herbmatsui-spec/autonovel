# src/backend/routers/orchestrated.py
"""マルチエージェントオーケストレーション API エンドポイント。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from pydantic import BaseModel, Field

from src.backend import database
from src.backend.database.repository import BookRepository
from src.backend.observability.health import metrics
from src.backend.rate_limit import generate_limiter
from src.backend.tasks.generation_tasks import generate_chapter_orchestrated_task
from src.backend.tasks.huey import huey

router = APIRouter(tags=["orchestrated"])
logger = logging.getLogger(__name__)


class OrchestratedGenerateRequest(BaseModel):
    """オーケストレーション版生成リクエスト。"""

    book_id: int = Field(default=1, ge=1, description="作品ID")
    branch_id: int = Field(default=1, ge=1, description="ブランチID")
    ep_num: int = Field(default=1, ge=1, description="エピソード番号")
    title: str = Field(..., min_length=1, max_length=200, description="作品タイトル")
    synopsis: str = Field(default="", description="あらすじ")
    target_eps: int = Field(default=10, ge=1, le=100, description="目標総話数")
    concept: str = Field(default="", description="コンセプト")
    genre: str = Field(default="fantasy", description="ジャンル")
    keywords: str = Field(default="", description="キーワード")
    target_word_count: int = Field(default=3000, ge=500, le=10000, description="目標文字数")
    style_tag: str | None = Field(default=None, description="文体タグ")
    llm_config: dict[str, Any] | None = Field(default=None, description="LLM設定")


class OrchestratedGenerateResponse(BaseModel):
    """生成起動レスポンス。"""

    task_id: str
    status: str
    message: str


@router.post("/generate", response_model=OrchestratedGenerateResponse)
async def generate_orchestrated(
    input_data: OrchestratedGenerateRequest,
    request: Request,
    session=Depends(database.get_db),
) -> OrchestratedGenerateResponse:
    """マルチエージェントオーケストレーションによる章生成をキューに投入。"""
    generate_limiter.check(request)

    try:
        # リクエストを dict に変換
        params: dict[str, Any] = input_data.model_dump()

        # Huey 非同期タスクとして投入
        task_result = generate_chapter_orchestrated_task(params)
        huey_task_id = str(task_result.id)
        params["task_id"] = huey_task_id

        # DB レコードを作成
        repo = BookRepository(session)
        repo.create_task(task_id=huey_task_id, status="running")

        metrics.increment("orchestrated_tasks_enqueued")
        logger.info("Enqueued orchestrated generation task: task_id=%s", huey_task_id)

        return OrchestratedGenerateResponse(
            task_id=huey_task_id,
            status="pending",
            message=f"オーケストレーション生成タスク ID: {huey_task_id} を投入しました。ステータスを /orchestrated/status/{huey_task_id} で確認してください。",
        )
    except Exception as e:
        logger.exception("Internal orchestrated generation error")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/status/{task_id}")
async def get_orchestrated_task_status(task_id: str) -> dict[str, Any]:
    """オーケストレーションタスクのステータス取得。"""
    result = huey.result(task_id)
    if result is None:
        logger.info("Orchestrated task status polled (pending): task_id=%s", task_id)
        return {"task_id": task_id, "status": "pending"}

    if isinstance(result, dict) and result.get("error"):
        logger.info(
            "Orchestrated task status polled (failed): task_id=%s error=%s",
            task_id,
            result["error"],
        )
        return {"task_id": task_id, "status": "failed", "error": result["error"], "result": result}

    logger.info("Orchestrated task status polled (completed): task_id=%s", task_id)
    return {"task_id": task_id, "status": "completed", "result": result}


@router.delete("/task/{task_id}")
async def cancel_orchestrated_task(task_id: str) -> dict[str, str]:
    """オーケストレーションタスクをキャンセル。"""
    try:
        huey.revoke_by_id(task_id)
    except Exception:
        logger.warning("Failed to revoke huey task_id=%s", task_id)

    repo = BookRepository()
    repo.update_task_status(task_id, "cancelled")

    return {"task_id": task_id, "status": "cancelled"}


@router.get("/export/{book_id}")
async def export_orchestrated_package(
    book_id: int = Path(ge=1),
    session=Depends(database.get_db),
):
    """オーケストレーション版の納品パッケージ (ZIP) をエクスポート。"""
    import urllib.parse
    from fastapi import Response

    logger.info("Orchestrated export requested: book_id=%s", book_id)
    metrics.increment("orchestrated_exports_attempted")

    repo = BookRepository(session)
    from src.agents.marketing import MarketingAgent
    from src.services.llm.factory import get_llm_adapter

    # MarketingAgent で ZIP 生成
    llm_adapter = get_llm_adapter()
    agent = MarketingAgent(repo=repo, llm=llm_adapter)
    zip_bytes, zip_filename = await agent.create_export_package(book_id)

    encoded_filename = urllib.parse.quote(zip_filename)
    ascii_filename = zip_filename.encode("ascii", "ignore").decode("ascii") or "export.zip"

    logger.info(
        "Orchestrated export succeeded: book_id=%s bytes=%d filename=%s",
        book_id,
        len(zip_bytes),
        zip_filename,
    )
    metrics.increment("orchestrated_exports_succeeded")

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"
            ),
            "Cache-Control": "no-store",
        },
    )
