import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
import logging
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.container import Container
from config.cors_config import get_allowed_origins
from config.logging_config import setup_logging

from src.backend.auth import validate_api_key_or_raise
from src.backend.database import UnitOfWork, init_db
from src.backend.error_handlers import register_error_handlers
from src.backend.routers import (
    books,
    commercial,
    episodes,
    health,
    issues,
    marketing,
    metrics,
    misc,
    novel,
    patches,
    plots,
    prompt_versions,
    tasks,
)
from src.backend.task_helpers import create_task as _create_task
from src.backend.tasks import execute_service_workflow
from src.core.observability import TraceContext
from src.models.api_schemas import (
    CritiqueOptimizeRequest,
    EasyModeRequest,
    RefineEroticRequest,
)

logger = logging.getLogger(__name__)

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


def generate_task_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


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


async def add_security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


_rate_limit_store: dict[str, list[float]] = defaultdict(list)
_RATE_LIMIT_MAX_REQUESTS = 100
_RATE_LIMIT_WINDOW_SECONDS = 60


async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW_SECONDS

    _rate_limit_store[client_ip] = [t for t in _rate_limit_store[client_ip] if t > window_start]

    if len(_rate_limit_store[client_ip]) >= _RATE_LIMIT_MAX_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"error": "Too Many Requests", "detail": "リクエスト数が制限を超えました。"},
        )

    _rate_limit_store[client_ip].append(now)
    return await call_next(request)


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


class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=30.0)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={
                    "error": "Gateway Timeout",
                    "detail": "リクエストがタイムアウトしました。",
                },
            )


def create_app() -> FastAPI:
    """FastAPIアプリケーションを構築して返すファクトリ関数。"""
    setup_logging()

    application = FastAPI(
        title="覇権小説エンジン API",
        version="3.0",
        lifespan=lifespan,
    )

    # エラーハンドラ
    register_error_handlers(application)

    # ミドルウェア
    application.add_middleware(TimeoutMiddleware)
    configure_cors(application)

    application.middleware("http")(rate_limit_middleware)
    application.middleware("http")(add_security_headers_middleware)
    application.middleware("http")(add_trace_id_middleware)

    # ルーター登録
    router_list = [
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
        commercial,
    ]
    for r in router_list:
        application.include_router(r.router)

    return application


app = create_app()


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
