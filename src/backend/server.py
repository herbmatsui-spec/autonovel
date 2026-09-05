"""FastAPI アプリケーションのエントリポイント。"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.api.admin_phase2 import (
    enrichment_router as admin_enrichment_router,
    rag_router as admin_rag_router,
    router as admin_audit_router,
)
from src.backend.config import settings
from src.backend.database import init_db
from src.backend.error_handlers import register_error_handlers
from src.backend.logging_config import configure as configure_logging
from src.backend.observability.health import build_health_payload, metrics
from src.backend.routers import (
    anti_ai,
    books,
    branches,
    commercial,
    easy_mode,
    editor,
    episodes,
    export,
    graph,
    illustrations,
    issues,
    marketing,
    misc,
    multimedia,
    novel,
    patches,
    plots,
    prompt_versions,
    streaming,
    styles,
    system,
    tasks,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """アプリケーション起動時にログ設定と DB 初期化を行う lifespan ハンドラ。"""
    configure_logging()
    init_db()
    yield


app = FastAPI(title=f"{settings.APP_NAME} Backend", version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

register_error_handlers(app)


# コアルーター登録
app.include_router(easy_mode.router, prefix="/easy_mode", tags=["easy_mode"])
if settings.APP_ENV == "development":
    app.include_router(easy_mode.router, prefix="/api/easy-mode", tags=["easy-mode"])
app.include_router(streaming.router, prefix="/easy_mode", tags=["streaming"])
app.include_router(styles.router)
app.include_router(graph.router)
app.include_router(editor.router)
app.include_router(system.router)
app.include_router(export.router)

# 管理者・監査ルーター登録
app.include_router(admin_audit_router)
app.include_router(admin_rag_router)
app.include_router(admin_enrichment_router)

# 各ドメインルーターの静的登録
app.include_router(books.router)
app.include_router(plots.router)
app.include_router(episodes.router)
app.include_router(tasks.router)
app.include_router(patches.router)
app.include_router(issues.router)
app.include_router(marketing.router)
app.include_router(prompt_versions.router)
app.include_router(misc.router)
app.include_router(novel.router)
app.include_router(commercial.router)
app.include_router(illustrations.router)
app.include_router(multimedia.router, prefix="/multimedia", tags=["multimedia"])
app.include_router(branches.router)
app.include_router(anti_ai.router)


@app.get("/health")
async def health() -> dict[str, object]:
    """ヘルスチェックエンドポイント (Phase 5: Step 55-57 拡充版)。

    DB 接続・Huey 生存確認・基本メトリクスを含めた総合ステータスを返す。
    全コンポーネント正常時は ``status=ok``、いずれか異常時は ``degraded``。
    互換性のため簡易 ``{"status": "ok"}`` のスーパーセットを返す。
    """
    logger.info("Health check invoked")
    return await build_health_payload()


@app.get("/metrics")
async def get_metrics() -> dict[str, int]:
    """メトリクスエンドポイント (Phase 5: Step 58)。

    プロセス内カウンタ (タスク投入数 / 完了数 / 失敗数 / エクスポート数 /
    ヘルスチェック呼出数) のスナップショットを返す。
    """
    return metrics.snapshot()
