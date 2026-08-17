import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import asyncio
import importlib
import logging
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.constants import (
    LONG_RUNNING_TIMEOUT_SEC as _LONG_RUNNING_TIMEOUT_SEC,
)
from config.constants import (
    RATE_LIMIT_MAX_REQUESTS as _RATE_LIMIT_MAX_REQUESTS,
)
from config.constants import (
    RATE_LIMIT_WINDOW_SECONDS as _RATE_LIMIT_WINDOW_SECONDS,
)
from config.cors_config import get_allowed_origins
from config.logging_config import setup_logging
from src.backend.auth import validate_api_key_or_raise
from src.backend.background import BackgroundReporter, ProgressState
from src.backend.database import init_db
from src.backend.error_handlers import register_error_handlers
from src.backend.rate_limit import RedisRateLimiter
from src.services.redis_cache import RedisCacheService
from src.backend.observability.metrics import MetricsMiddleware
from src.backend.rate_limit import RedisRateLimiter
from src.core.container import AppContainer
from src.core.observability import TraceContext
from src.core.opentelemetry import setup_opentelemetry
from src.easy_mode.pipeline import EasyModePipeline, PipelineConfig
from src.models.api_schemas import (
    CritiqueOptimizeRequest,
    EasyModeRequest,
    RefineEroticRequest,
)
from src.services.redis_cache import RedisCacheService

logger = logging.getLogger(__name__)
# Redis rate limiter (initialized in lifespan)
_redis_rate_limiter: Optional[RedisRateLimiter] = None

setup_logging()


def create_pipeline_config_from_request(req: EasyModeRequest) -> PipelineConfig:
    """EasyModeRequest から PipelineConfig を作成"""
    return PipelineConfig(
        genre=req.genre,
        target_episodes=req.target_eps,
        max_rewrite_iterations=3,
        target_audit_score=95.0,
        enable_spice_guard=True,
    )


# Startup DB migration using lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # OpenTelemetry 初期化
    try:
        from src.core.opentelemetry import setup_opentelemetry
        setup_opentelemetry(
            service_name="kaku-hegemony-engine",
            sample_rate=0.1,  # 本番は 0.1 (10%)
            enable_console_exporter=False,
        )
        logger.info("OpenTelemetry auto-instrumentation initialized")
    except Exception as e:
        logger.warning(f"OpenTelemetry initialization failed: {e}")

    try:
        db_manager = AppContainer.db()
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
        logger.info("シャットダウン処理を開始...")
        try:
            # SQLite 接続のクローズ
            db_manager = AppContainer.db()
            if db_manager and hasattr(db_manager, "engine") and db_manager.engine:
                # データベースの非同期コネクションプールを強制的に破棄する
                await db_manager.engine.dispose()
                logger.info("データベースのコネクションを正常にクローズしました。")

            # ChromaDB 接続のクローズ
            chroma_provider = AppContainer.chroma_client_provider()
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
_DEFAULT_TIMEOUT_SEC = 30.0
_rate_limit_lock = asyncio.Lock()

# 長時間実行されるLLM生成系エンドポイント（タイムアウトを延長）
LONG_RUNNING_PATHS = frozenset(
    {
        "/api/easy_mode/generate",
        "/api/refine_erotic",
        "/api/critique/optimize",
        "/api/episodes/generate",
        "/api/plots/generate",
    }
)


async def rate_limit_middleware(request: Request, call_next):
    global _redis_rate_limiter

    client_ip = request.client.host if request.client else "unknown"

    # Lazy initialization (Redis not available at import time)
    if _redis_rate_limiter is None:
        redis = RedisCacheService()
        _redis_rate_limiter = RedisRateLimiter(
            redis=redis,
            max_requests=_RATE_LIMIT_MAX_REQUESTS,
            window_seconds=_RATE_LIMIT_WINDOW_SECONDS,
        )

    allowed = await _redis_rate_limiter.is_allowed(client_ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"error": "Too Many Requests", "detail": "リクエスト数が制限を超えました。"},
        )
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
        # LLM生成系エンドポイントは長時間実行されるため、タイムアウトを延長
        timeout = (
            _LONG_RUNNING_TIMEOUT_SEC
            if any(request.url.path.startswith(p) for p in LONG_RUNNING_PATHS)
            else _DEFAULT_TIMEOUT_SEC
        )

        try:
            return await asyncio.wait_for(call_next(request), timeout=timeout)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={
                    "error": "Gateway Timeout",
                    "detail": f"リクエストがタイムアウトしました（{timeout}秒）。",
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

    # HTTP メトリクスミドルウェア（最外側で全リクエスト計測）
    application.middleware("http")(MetricsMiddleware())
    application.middleware("http")(rate_limit_middleware)
    application.middleware("http")(add_security_headers_middleware)
    application.middleware("http")(add_trace_id_middleware)

    # ルーター登録（遅延ロード）
    router_modules = [
        "src.backend.routers.health",
        "src.backend.routers.books",
        "src.backend.routers.plots",
        "src.backend.routers.episodes",
        "src.backend.routers.tasks",
        "src.backend.routers.patches",
        "src.backend.routers.issues",
        "src.backend.routers.marketing",
        "src.backend.routers.prompt_versions",
        "src.backend.routers.metrics",
        "src.backend.routers.misc",
        "src.backend.routers.novel",
        "src.backend.routers.commercial",
        "src.backend.routers.easy_mode",
        "src.backend.routers.illustrations",
    ]
    for module_path in router_modules:
        try:
            module = importlib.import_module(module_path)
            application.include_router(module.router)
        except ImportError as e:
            logger.error(f"Failed to load router {module_path}: {e}")

    return application


app = create_app()


@app.post("/api/refine_erotic")
async def refine_erotic(req: RefineEroticRequest):
    from src.backend.task_helpers import create_task as _create_task
    from src.backend.tasks import execute_service_workflow

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
    from src.backend.task_helpers import create_task as _create_task
    from src.core.container import AppContainer

    validate_api_key_or_raise(req.api_key)
    task_id = generate_task_id("easy")

    # 進捗管理用の状態を作成
    progress_state = ProgressState(
        is_running=True,
        task_id=task_id,
        repo=AppContainer.db(),
    )
    reporter = BackgroundReporter(progress_state)

    # 初期タスク作成（DBに保存）
    await _create_task(task_id, "かんたんモード生成を開始中...", total_steps=4)

    # PipelineConfigを作成
    config = create_pipeline_config_from_request(req)

    # 進捗コールバックを定義
    def progress_callback(stage: str, current: int, total: int):
        stage_messages = {
            "bible": ("Bible生成中", f"ジャンル設定反映中... ({current}/{total})"),
            "plot": ("プロット生成中", f"全{total}話の構成作成中... ({current}/{total})"),
            "writing": ("本文執筆中", f"第{current}話を執筆中... ({current}/{total})"),
            "episode_complete": ("話完了", f"第{current}話が完了 ({current}/{total})"),
            "finalizing": ("完結処理中", f"メタデータ生成中... ({current}/{total})"),
        }
        msg, sub_msg = stage_messages.get(stage, (stage, ""))
        reporter.update_progress(current, total, msg, sub_msg)

    config.progress_callback = progress_callback

    try:
        # エンジンを取得してパイプラインを実行
        container = AppContainer(api_key=req.api_key, db=AppContainer.db())
        engine = container.engine()

        pipeline = EasyModePipeline(engine, config)
        result = await pipeline.run()

        # 完了処理
        progress_state.is_running = False
        progress_state.message = "生成完了"
        progress_state.result_data = {
            "title": result.title,
            "concept": result.concept,
            "total_episodes": result.total_episodes,
            "total_words": sum(ep.word_count for ep in result.episodes),
            "average_audit_score": round(sum(ep.audit_score for ep in result.episodes) / len(result.episodes), 1) if result.episodes else 0,
            "genre": result.genre,
            "episodes": [
                {
                    "episode_num": ep.episode_num,
                    "title": ep.title,
                    "word_count": ep.word_count,
                    "audit_score": ep.audit_score,
                    "audit_passed": ep.audit_passed,
                    "rewrite_count": ep.rewrite_count,
                    "needs_human_review": ep.needs_human_review,
                }
                for ep in result.episodes
            ],
        }
        progress_state._save_to_db()

        logger.info(f"Easy mode pipeline completed: {task_id}")
        return {"task_id": task_id, "result": progress_state.result_data}

    except Exception as e:
        logger.error(f"Easy mode pipeline failed: {e}", exc_info=True)
        progress_state.is_running = False
        progress_state.error = str(e)
        progress_state._save_to_db()
        from fastapi import HTTPException
        raise HTTPException(
            status_code=500,
            detail=f"かんたんモード生成に失敗しました: {str(e)}"
        )


@app.post("/api/critique/optimize")
async def critique_optimize(req: CritiqueOptimizeRequest):
    from src.backend.task_helpers import create_task as _create_task
    from src.backend.tasks import execute_service_workflow

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