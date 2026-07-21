from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from src.models.api_schemas import MarketingGenerateRequest
from src.backend.engine_helpers import get_engine
from src.backend.task_helpers import create_task
from src.backend.tasks import execute_service_workflow
from src.core.observability import TraceContext
from src.backend.auth import validate_api_key_or_raise

router = APIRouter(tags=["marketing"])

@router.post("/api/marketing/generate")
async def generate_marketing(req: MarketingGenerateRequest):
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
            "latest_ep": req.latest_ep
        },
        trace_id=TraceContext.get_trace_id()
    )
    return {"task_id": task_id}

@router.post("/api/marketing/export_package/{book_id}")
async def export_package_post(book_id: int, api_key_req: Any):
    # Original server.py had a pass here
    # Keeping the endpoint for compatibility but as it was a no-op
    return {"message": "Export package POST is not implemented"}

@router.get("/api/marketing/export_package/{book_id}")
async def export_package_get(book_id: int, api_key: str):
    engine = get_engine(api_key)
    zip_data, zip_filename = await engine.marketing.create_export_package(book_id)
    return Response(
        content=zip_data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
    )
