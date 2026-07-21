import json
import logging
import os
import sys
import time
from typing import Any, Dict, Optional

from pydantic import BaseModel

from src.models.api_schemas import (
    EasyModeRequest,
    EpisodeGenerateRequest,
    EpisodeGenerateCandidatesRequest,
    PlanGenerationRequest,
    RetryFailedRequest,
    PlotExpandRequest,
    PlotExpandCandidatesRequest,
    PlotRebuildRequest,
    CritiqueOptimizeRequest,
    AuditPlanRequest,
    ChapterImportRequest,
    MarketingGenerateRequest,
    RefineEroticRequest,
    PatchActionRequest,
    PatchEditRequest,
    RollbackRequest,
    ResolveIssueRequest,
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


@app.middleware("http")
async def add_security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


from collections import defaultdict
from datetime import datetime, timedelta
import time

_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_MAX_REQUESTS = 100
_RATE_LIMIT_WINDOW_SECONDS = 60


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW_SECONDS

    _rate_limit_store[client_ip] = [t for t in _rate_limit_store[client_ip] if t > window_start]

    if len(_rate_limit_store[client_ip]) >= _RATE_LIMIT_MAX_REQUESTS:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=429,
            content={"error": "Too Many Requests", "detail": "リクエスト数が制限を超えました。"},
        )

    _rate_limit_store[client_ip].append(now)
    return await call_next(request)


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

# Request timeout configuration (Step 38)
from starlette.middleware.base import BaseHTTPMiddleware


class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            import asyncio

            return await asyncio.wait_for(call_next(request), timeout=30.0)
        except asyncio.TimeoutError:
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=504,
                content={
                    "error": "Gateway Timeout",
                    "detail": "リクエストがタイムアウトしました。",
                },
            )


app.add_middleware(TimeoutMiddleware)

from src.backend.routers import (
    commercial,
    health,
    books,
    plots,
    episodes,
    tasks,
    patches,
    issues,
    marketing,
    prompt_versions,
    metrics,
    misc,
    novel,
)

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


# 各ルーターに移譲済み:
# - /api/plots/*         → routers/plots.py
# - /api/episodes/*      → routers/episodes.py
# - /api/books/*         → routers/books.py
# - /api/patches/*       → routers/patches.py
# - /api/issues/*        → routers/issues.py
# - /api/marketing/*     → routers/marketing.py
# - /api/prompt_versions/* → routers/prompt_versions.py
# - /api/metrics/*       → routers/metrics.py
# - /api/narrative_metrics/* → routers/misc.py
# - /api/bibles/*        → routers/misc.py
# - /api/optimization_history/* → routers/misc.py
# - /api/produce, /status, /episodes, /report → routers/novel.py
# - /api/commercial/run  → routers/commercial.py

# server.py に残存するエンドポイント (既存ルータープレフィックスに適合しない為)
from src.backend.task_helpers import create_task as _create_task
from src.backend.auth import validate_api_key_or_raise


@app.post("/api/refine_erotic")
async def refine_erotic(req: RefineEroticRequest):
    validate_api_key_or_raise(req.api_key)
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
        trace_id=TraceContext.get_trace_id(),
    )
    return {"task_id": task_id}


# Heavy operations enqueued via Huey
@app.post("/api/easy_mode/generate")
async def generate_easy(req: EasyModeRequest):
    validate_api_key_or_raise(req.api_key)
    task_id = generate_task_id("easy")
    await _create_task(task_id, "タスクを開始中...", total_steps=3)
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
            "tone_vibe": req.tone_vibe,
        },
        trace_id=TraceContext.get_trace_id(),
    )
    return {"task_id": task_id}


@app.post("/api/critique/optimize")
async def critique_optimize(req: CritiqueOptimizeRequest):
    validate_api_key_or_raise(req.api_key)
    task_id = generate_task_id("critique")
    await _create_task(task_id, "品質分析を開始中...", total_steps=1)
    execute_service_workflow(
        task_id=task_id,
        api_key=req.api_key,
        config_dict=req.config,
        method_name="run_critique_optimization_workflow",
        kwargs={"book_id": req.book_id},
        trace_id=TraceContext.get_trace_id(),
    )
    return {"task_id": task_id}


# Marketing router endpoints moved to src/backend/routers/marketing.py


# Narrative Metrics trend endpoint moved to src/backend/routers/misc.py


# Prompt Metrics API endpoints moved to src/backend/routers/metrics.py
