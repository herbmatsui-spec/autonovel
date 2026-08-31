"""FastAPI アプリケーションのエントリポイント。"""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.backend.database import init_db
from src.backend.exceptions import AutoNovelException
from src.backend.logging_config import configure as configure_logging
from src.backend.observability import build_health_payload, metrics
from src.backend.routers import easy_mode


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """アプリケーション起動時にログ設定と DB 初期化を行う lifespan ハンドラ。"""
    configure_logging()
    init_db()
    yield


app = FastAPI(title="AutoNovel Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AutoNovelException)
async def autonovel_exception_handler(request: Request, exc: AutoNovelException) -> JSONResponse:
    """カスタム例外を一括で処理し、構造化されたJSONを返却するハンドラ"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.__class__.__name__, "detail": exc.detail},
    )

app.include_router(easy_mode.router, prefix="/easy_mode", tags=["easy_mode"])


@app.get("/health")
async def health() -> dict[str, object]:
    """ヘルスチェックエンドポイント (Phase 5: Step 55-57 拡充版)。

    DB 接続・Huey 生存確認・基本メトリクスを含めた総合ステータスを返す。
    全コンポーネント正常時は ``status=ok``、いずれか異常時は ``degraded``。
    互換性のため簡易 ``{"status": "ok"}`` のスーパーセットを返す。
    """
    import logging

    logging.getLogger(__name__).info("Health check invoked")
    return build_health_payload()


@app.get("/metrics")
async def get_metrics() -> dict[str, int]:
    """メトリクスエンドポイント (Phase 5: Step 58)。

    プロセス内カウンタ (タスク投入数 / 完了数 / 失敗数 / エクスポート数 /
    ヘルスチェック呼出数) のスナップショットを返す。
    """
    return metrics.snapshot()
