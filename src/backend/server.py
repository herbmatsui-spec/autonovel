import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional

from pydantic import BaseModel

from src.models.api_schemas import (
    EasyModeRequest, EpisodeGenerateRequest, EpisodeGenerateCandidatesRequest,
    PlanGenerationRequest, RetryFailedRequest, PlotExpandRequest,
    PlotExpandCandidatesRequest, PlotRebuildRequest, CritiqueOptimizeRequest,
    AuditPlanRequest, ChapterImportRequest, MarketingGenerateRequest,
    RefineEroticRequest, PatchActionRequest, PatchEditRequest,
    RollbackRequest, ResolveIssueRequest,
)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

logger = logging.getLogger(__name__)

from config.container import Container
from config.logging_config import setup_logging
from src.backend.database import UnitOfWork, init_db
from src.backend.engine import UltimateHegemonyEngine
from src.backend.tasks import execute_service_workflow

setup_logging()

# Startup DB migration using lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        db_manager = Container.db()
        init_db(db_manager.db_path)
        logger.info("Database initialization complete.")
        yield
    except Exception:
        import traceback
        logger.error(traceback.format_exc())
        raise
    except BaseException as e:
        logger.critical(f"サーバーが強制終了しました: {type(e).__name__} - {e}")
        raise
    finally:
        logger.info("シャットダウン処理を開始します...")
        try:
            # SQLite 接続のクローズ
            db_manager = Container.db()
            if db_manager and hasattr(db_manager, "engine") and db_manager.engine:
                # データベースの非同期コネクションプールを強制的に破棄する
                await db_manager.engine.dispose()
                logger.info("データベースのコネクションを正常にクローズしました。")

            # ChromaDB 接続のクローズ
            chroma_provider = Container.chroma_client_provider()
            if chroma_provider:
                chroma_provider.close()
                logger.info("ChromaDB のコネクションを正常にクローズしました。")
        except Exception as e:
            logger.error(f"リソース解放中にエラーが発生しました: {e}")
        logger.info("全てのリソースを解放しました。サーバーを終了します。")

import uuid


def generate_task_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


from fastapi import Request

from src.core.observability import TraceContext

app = FastAPI(title="覇権小説エンジン API", version="3.0", lifespan=lifespan)

from src.backend.error_handlers import register_error_handlers
register_error_handlers(app)

@app.middleware("http")
async def add_trace_id_middleware(request: Request, call_next):
    # リクエストヘッダーに X-Trace-ID があれば使用し、なければ UUID を生成
    trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())

    # TraceContext を使用してコンテキストにセット
    TraceContext.set_trace_id(trace_id)

    try:
        response = await call_next(request)
        # レスポンスヘッダーにも Trace ID を付与して返却
        response.headers["X-Trace-ID"] = trace_id
        return response
    finally:
        # リクエスト終了後にコンテキストをクリーンアップ
        TraceContext.clear()

# CORS middleware
from config.cors_config import get_allowed_origins

def configure_cors(app: FastAPI):
    allowed_origins = get_allowed_origins()
    logger.info(f"CORS allowed origins: {allowed_origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

configure_cors(app)

from src.backend.routers import commercial, health, books, plots, episodes, tasks, patches, issues, marketing, prompt_versions, metrics, misc, novel

app.include_router(health.router)
app.include_router(books.router)
app.include_router(plots.router)
app.include_router(episodes.router)
app.include_router(tasks.router)
app.include_router(patches.router)
app.include_router(issues.router)
app.include_router(marketing.router)
app.include_router(prompt_versions.router)
app.include_router(metrics.router)
app.include_router(misc.router)
app.include_router(novel.router)
app.include_router(commercial.router)



# Deprecated narrative metrics endpoint moved to src/backend/routers/misc.py


from src.backend.engine_helpers import get_engine as resolve_engine




# Bible and Optimization History endpoints moved to src/backend/routers/misc.py

# Patches router endpoints moved to src/backend/routers/patches.py

# Prompt Versions router endpoints moved to src/backend/routers/prompt_versions.py



from src.backend.task_helpers import create_task as _create_task

@app.post("/api/refine_erotic")
async def refine_erotic(req: RefineEroticRequest):
    task_id = generate_task_id("refine_erotic")
    await _create_task(task_id, "官能研磨タスクを開始中...", total_steps=1)

    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="refine_erotic_workflow",
        kwargs={
            "book_id": req.book_id,
            "ep_num": req.ep_num,
            "intensity": req.intensity,
            "platform_preset": req.platform_preset,
        },
        trace_id=TraceContext.get_trace_id()
    )
    return {"task_id": task_id}

# Heavy operations enqueued via Huey
@app.post("/api/easy_mode/generate")
async def generate_easy(req: EasyModeRequest):
    task_id = generate_task_id("easy")
    await _create_task(task_id, "タスクを開始中...", total_steps=3)

    # Enqueue task
    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="full_auto_workflow",
        kwargs={
            "genre": req.genre,
            "keywords": req.keywords,
            "archetype_key": req.archetype_key,
            "target_eps": req.target_eps,
            "initial_limit": req.initial_limit,
            "word_count": req.word_count,
            "concept": req.concept,
            "tone_vibe": req.tone_vibe
        },
        trace_id=TraceContext.get_trace_id()
    )
    return {"task_id": task_id}

@app.post("/api/plots/plan_generation")
async def plan_generation(req: PlanGenerationRequest):
    task_id = generate_task_id("plan_gen")
    await _create_task(task_id, "企画作成を開始中...", total_steps=1)
    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="plan_generation_workflow",
        kwargs={"params": req.params},
        trace_id=TraceContext.get_trace_id()
    )
    return {"task_id": task_id}

@app.post("/api/episodes/retry_failed")
async def retry_failed_episodes(req: RetryFailedRequest):
    task_id = generate_task_id("retry_failed")
    await _create_task(task_id, "失敗エピソードの修復を開始中...", total_steps=1)
    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="retry_failed_episodes_workflow",
        kwargs={
            "book_id": req.book_id,
            "passion": req.passion,
            "word_count": req.word_count
        },
        trace_id=TraceContext.get_trace_id()
    )
    return {"task_id": task_id}

@app.post("/api/episodes/generate")
async def generate_episodes(req: EpisodeGenerateRequest):
    task_id = generate_task_id("write")
    await _create_task(task_id, "執筆タスクを開始中...", total_steps=req.write_to - req.write_from + 1)

    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="episode_writing_workflow",
        kwargs={
            "book_id": req.book_id,
            "write_from": req.write_from,
            "write_to": req.write_to,
            "passion": req.passion,
            "word_count": req.word_count,
            "do_refine": req.do_refine,
            "env_state": req.env_state,
            "pipeline_mode": req.pipeline_mode,
            "mode": "final"
        },
        trace_id=TraceContext.get_trace_id()
    )
    return {"task_id": task_id}

@app.post("/api/episodes/generate_candidates")
async def generate_episodes_candidates(req: EpisodeGenerateCandidatesRequest):
    task_id = generate_task_id("write_candidates")
    await _create_task(task_id, "本文候補案を生成中...", total_steps=req.write_to - req.write_from + 1)

    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="episode_writing_workflow",
        kwargs={
            "book_id": req.book_id,
            "write_from": req.write_from,
            "write_to": req.write_to,
            "passion": req.passion,
            "word_count": req.word_count,
            "do_refine": req.do_refine,
            "env_state": req.env_state,
            "pipeline_mode": req.pipeline_mode,
            "mode": "candidates"
        },
        trace_id=TraceContext.get_trace_id()
    )
    return {"task_id": task_id}

@app.post("/api/plots/expand")
async def expand_plots(req: PlotExpandRequest):
    task_id = generate_task_id("plot_expand")
    await _create_task(task_id, "プロット作成を開始中...", total_steps=req.gen_to - req.gen_from + 1)

    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="plot_expansion_workflow",
        kwargs={
            "book_id": req.book_id,
            "gen_from": req.gen_from,
            "gen_to": req.gen_to,
            "mode": "final"
        },
        trace_id=TraceContext.get_trace_id()
    )
    return {"task_id": task_id}

@app.post("/api/plots/expand_candidates")
async def expand_plots_candidates(req: PlotExpandCandidatesRequest):
    task_id = generate_task_id("plot_candidates")
    await _create_task(task_id, "プロット候補案を生成中...", total_steps=req.gen_to - req.gen_from + 1)

    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="plot_expansion_workflow",
        kwargs={
            "book_id": req.book_id,
            "gen_from": req.gen_from,
            "gen_to": req.gen_to,
            "mode": "candidates"
        },
        trace_id=TraceContext.get_trace_id()
    )
    return {"task_id": task_id}

@app.post("/api/plots/rebuild")
async def rebuild_plots(req: PlotRebuildRequest):
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
        "last_updated": time.time()
    }
    await db.save_internal_state(
        f"task_status:{task_id}",
        json.dumps(initial_state),
        time.strftime('%Y-%m-%d %H:%M:%S')
    )

    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="plot_rebuild_workflow",
        kwargs={
            "params": req.params
        },
        trace_id=TraceContext.get_trace_id()
    )
    return {"task_id": task_id}

@app.post("/api/critique/optimize")
async def critique_optimize(req: CritiqueOptimizeRequest):
    task_id = generate_task_id("critique")

    await _create_task(task_id, "品質分析を開始中...", total_steps=1)

    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="run_critique_optimization_workflow",
        kwargs={
            "book_id": req.book_id
        },
        trace_id=TraceContext.get_trace_id()
    )
    return {"task_id": task_id}

# Synchronous endpoints (lightweight)
@app.post("/api/plots/audit")
async def audit_plan(req: AuditPlanRequest):
    engine = resolve_engine(req.api_key)
    res = await engine.planner.audit_producer_plan(
        req.genre,
        req.keywords, req.trend_memo,
        sanctuary=req.sanctuary,
        originality_score=req.originality_score,
        platform=req.platform
    )
    if not res:
        from src.core.exceptions import AppError
        raise AppError("Audit failed")
    return {
        "refined_keywords": res.refined_keywords,
        "refined_concept": res.refined_concept,
        "refined_mc_suggestion": res.refined_mc_suggestion,
        "recommended_tropes": res.recommended_tropes,
        "candidates": [c.model_dump() for c in res.candidates]
    }

@app.post("/api/chapters/import")
async def import_chapter(req: ChapterImportRequest):
    task_id = generate_task_id("import")
    await _create_task(task_id, "手書き原稿のインポートと研磨を開始中...", total_steps=1)

    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict={},
        method_name="chapter_import_workflow",
        kwargs={
            "book_id": req.book_id,
            "ep_num": req.ep_num,
            "import_text": req.import_text,
            "do_refine": req.do_refine
        },
        trace_id=TraceContext.get_trace_id()
    )
    return {"task_id": task_id}

# Marketing router endpoints moved to src/backend/routers/marketing.py



# Narrative Metrics trend endpoint moved to src/backend/routers/misc.py



# Prompt Metrics API endpoints moved to src/backend/routers/metrics.py


