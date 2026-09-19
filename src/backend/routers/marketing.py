from typing import Any, List

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from src.backend.auth import get_prompt_manager, validate_api_key_or_raise
from src.backend.engine_helpers import get_engine
from src.backend.task_helpers import create_task
from src.backend.tasks import execute_service_workflow
from src.core.observability import TraceContext
from src.models.api_schemas import MarketingExportRequest, MarketingGenerateRequest, CatchphraseGenerateRequest
from src.agents.marketing import MarketingAgent
from src.domain.schemas.marketing import CatchphraseItem

router = APIRouter(tags=["marketing"])


@router.post("/api/marketing/generate")
async def generate_marketing(
    req: MarketingGenerateRequest,
    prompt_manager: Any = Depends(get_prompt_manager),
):
    validate_api_key_or_raise(req.api_key)
    import time

    task_id = f"marketing_{int(time.time())}"
    await create_task(task_id, "マーケティング情報の生成を開始中...", total_steps=1)

    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict={},
        method_name="marketing_generation_workflow",
        kwargs={
            "book_id": req.book_id,
            "latest_ep": req.latest_ep,
            "prompt_manager": prompt_manager,
        },
        trace_id=TraceContext.get_trace_id(),
    )
    return {"task_id": task_id}


@router.post("/api/marketing/export_package/{book_id}")
async def export_package_post(book_id: int, req: MarketingExportRequest):
    """作品データ一式 (本文 / 設定 / プロット / JSON) を ZIP で返す."""
    validate_api_key_or_raise(req.api_key)
    engine = get_engine(req.api_key)
    zip_data, zip_filename = await engine.marketing.create_export_package(book_id)
    return Response(
        content=zip_data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )


@router.get("/api/marketing/export_package/{book_id}")
async def export_package_get(book_id: int, api_key: str):
    engine = get_engine(api_key)
    zip_data, zip_filename = await engine.marketing.create_export_package(book_id)
    return Response(
        content=zip_data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )


@router.post("/api/marketing/catchphrases")
async def generate_catchphrases(
    req: CatchphraseGenerateRequest,
):
    """カクヨム用キャッチコピーを生成するエンドポイント"""
    await validate_api_key_or_raise(req.api_key)
    
    # コンテナからMarketingAgentを直接取得
    from src.core.container.app import AppContainer
    container = AppContainer(api_key=req.api_key)
    marketing_agent = container.marketing()
    
    # キャッチコピーを生成
    catchphrases = await marketing_agent.generate_viral_catchphrases(
        project_settings=req.project_settings,
        candidate_count=req.candidate_count,
    )
    
    # 結果を返す
    return catchphrases