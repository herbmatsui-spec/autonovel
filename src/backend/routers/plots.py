from fastapi import APIRouter, Depends

from src.backend.auth import require_api_key
from src.backend.database.uow import UnitOfWork
from src.backend.engine_helpers import get_engine as resolve_engine
from src.backend.response_helpers import api_success
from src.backend.router_helpers import workflow_endpoint
from src.backend.task_helpers import create_task as _create_task
from src.backend.utils.id_generator import generate_prefixed_id as generate_task_id
from src.core.container import AppContainer
from src.core.exceptions import AppError
from src.core.observability import TraceContext
from src.models.api_schemas import (
    AuditPlanRequest,
    PlanGenerationRequest,
    PlotExpandCandidatesRequest,
    PlotExpandRequest,
    PlotRebuildRequest,
)

router = APIRouter(prefix="/api/plots", tags=["plots"])


@router.get("/{book_id}")
async def get_plots(book_id: int):
    async with UnitOfWork(AppContainer.db()) as uow:
        plots = await uow.plots.get_all_plots(book_id)
    return [
        {
            "ep_num": p.ep_num,
            "title": p.title,
            "summary": p.summary,
            "detailed_blueprint": p.detailed_blueprint,
            "tension": p.tension,
            "is_catharsis": p.is_catharsis,
            "status": p.status,
        }
        for p in plots
    ]




@workflow_endpoint("plot_plan_generation")
@router.post("/plan_generation")
async def plan_generation(req: PlanGenerationRequest, api_key: str = Depends(require_api_key)):
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("plan_gen")
    await _create_task(task_id, "企画作成を開始中...", total_steps=1)
    execute_service_workflow(
        task_id=task_id,
        api_key=api_key,
        config_dict=req.config,
        method_name="plan_generation_workflow",
        kwargs={"params": req.params},
        trace_id=TraceContext.get_trace_id(),
    )
    return api_success({"task_id": task_id}, "企画生成を開始しました")


@workflow_endpoint("plot_expand")
@router.post("/expand")
async def expand_plots(req: PlotExpandRequest, api_key: str = Depends(require_api_key)):
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("plot_expand")
    await _create_task(
        task_id, "プロット作成を開始中...", total_steps=req.gen_to - req.gen_from + 1
    )
    execute_service_workflow(
        task_id=task_id,
        api_key=api_key,
        config_dict=req.config,
        method_name="plot_expansion_workflow",
        kwargs={
            "book_id": req.book_id,
            "gen_from": req.gen_from,
            "gen_to": req.gen_to,
            "mode": "final",
        },
        trace_id=TraceContext.get_trace_id(),
    )
    return api_success({"task_id": task_id}, "プロット展開を開始しました")


@workflow_endpoint("plot_expand_candidates")
@router.post("/expand_candidates")
async def expand_plots_candidates(req: PlotExpandCandidatesRequest, api_key: str = Depends(require_api_key)):
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("plot_candidates")
    await _create_task(
        task_id, "プロット候補案を生成中...", total_steps=req.gen_to - req.gen_from + 1
    )
    execute_service_workflow(
        task_id=task_id,
        api_key=api_key,
        config_dict=req.config,
        method_name="plot_expansion_workflow",
        kwargs={
            "book_id": req.book_id,
            "gen_from": req.gen_from,
            "gen_to": req.gen_to,
            "mode": "candidates",
        },
        trace_id=TraceContext.get_trace_id(),
    )
    return api_success({"task_id": task_id}, "プロット候補生成を開始しました")


@workflow_endpoint("plot_rebuild")
@router.post("/rebuild")
async def rebuild_plots(req: PlotRebuildRequest, api_key: str = Depends(require_api_key)):
    import json
    import time

    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("plot_rebuild")
    db = AppContainer.db()
    initial_state = {
        "is_running": True,
        "current_step": 0,
        "total_steps": 1,
        "message": "プロット再構築を開始中...",
        "sub_message": "キューの待機中",
        "streaming_text": "",
        "logs": [f"[{time.strftime('%H:%M:%S')}] 🚀 プロット再構築タスクを登録しました。"],
        "error": None,
        "result_data": None,
        "token_usage": {"prompt": 0, "completion": 0, "calls": 0},
        "start_time": time.time(),
        "last_updated": time.time(),
    }
    await db.save_internal_state(
        f"task_status:{task_id}", json.dumps(initial_state), time.strftime("%Y-%m-%d %H:%M:%S")
    )
    execute_service_workflow(
        task_id=task_id,
        api_key=api_key,
        config_dict=req.config,
        method_name="plot_rebuild_workflow",
        kwargs={"params": req.params},
        trace_id=TraceContext.get_trace_id(),
    )
    return api_success({"task_id": task_id}, "プロット再構築を開始しました")


@router.post("/audit")
async def audit_plan(req: AuditPlanRequest, api_key: str = Depends(require_api_key)):
    engine = resolve_engine(api_key)
    res = await engine.planner.audit_producer_plan(
        req.genre,
        req.keywords,
        req.trend_memo,
        sanctuary=req.sanctuary,
        originality_score=req.originality_score,
        platform=req.platform,
    )
    if not res:
        raise AppError("Audit failed")
    return api_success(
        {
            "refined_keywords": res.refined_keywords,
            "refined_concept": res.refined_concept,
            "refined_mc_suggestion": res.refined_mc_suggestion,
            "recommended_tropes": res.recommended_tropes,
            "candidates": [c.model_dump() for c in res.candidates],
        },
        "企画監査を実行しました",
    )
