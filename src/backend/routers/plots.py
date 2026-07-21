from fastapi import APIRouter
from config.container import Container
from src.backend.database.uow import UnitOfWork
from src.models.api_schemas import (
    PlanGenerationRequest,
    PlotExpandRequest,
    PlotExpandCandidatesRequest,
    PlotRebuildRequest,
    CritiqueOptimizeRequest,
    AuditPlanRequest,
)
from src.backend.task_helpers import create_task as _create_task
from src.backend.engine_helpers import get_engine as resolve_engine
from src.core.observability import TraceContext
from src.core.exceptions import AppError
from src.backend.auth import validate_api_key_or_raise

router = APIRouter(prefix="/api/plots", tags=["plots"])


@router.get("/{book_id}")
async def get_plots(book_id: int):
    async with UnitOfWork(Container.db()) as uow:
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


def generate_task_id(prefix: str) -> str:
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@router.post("/plan_generation")
async def plan_generation(req: PlanGenerationRequest):
    validate_api_key_or_raise(req.api_key)
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("plan_gen")
    await _create_task(task_id, "企画作成を開始中...", total_steps=1)
    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="plan_generation_workflow",
        kwargs={"params": req.params},
        trace_id=TraceContext.get_trace_id(),
    )
    return {"task_id": task_id}


@router.post("/expand")
async def expand_plots(req: PlotExpandRequest):
    validate_api_key_or_raise(req.api_key)
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("plot_expand")
    await _create_task(
        task_id, "プロット作成を開始中...", total_steps=req.gen_to - req.gen_from + 1
    )
    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
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
    return {"task_id": task_id}


@router.post("/expand_candidates")
async def expand_plots_candidates(req: PlotExpandCandidatesRequest):
    validate_api_key_or_raise(req.api_key)
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("plot_candidates")
    await _create_task(
        task_id, "プロット候補案を生成中...", total_steps=req.gen_to - req.gen_from + 1
    )
    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
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
    return {"task_id": task_id}


@router.post("/rebuild")
async def rebuild_plots(req: PlotRebuildRequest):
    validate_api_key_or_raise(req.api_key)
    import time, json
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("plot_rebuild")
    db = Container.db()
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
        api_key=req.api_key,
        config_dict=req.config,
        method_name="plot_rebuild_workflow",
        kwargs={"params": req.params},
        trace_id=TraceContext.get_trace_id(),
    )
    return {"task_id": task_id}


@router.post("/audit")
async def audit_plan(req: AuditPlanRequest):
    validate_api_key_or_raise(req.api_key)
    engine = resolve_engine(req.api_key)
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
    return {
        "refined_keywords": res.refined_keywords,
        "refined_concept": res.refined_concept,
        "refined_mc_suggestion": res.refined_mc_suggestion,
        "recommended_tropes": res.recommended_tropes,
        "candidates": [c.model_dump() for c in res.candidates],
    }
