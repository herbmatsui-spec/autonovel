"""FastAPI アプリケーションのエントリポイント。"""
from __future__ import annotations

import importlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.config import settings
from src.backend.database import init_db
from src.backend.error_handlers import register_error_handlers
from src.backend.logging_config import configure as configure_logging
from src.backend.observability.health import build_health_payload, metrics
from src.backend.routers import easy_mode, editor, graph, streaming

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




app.include_router(easy_mode.router, prefix="/easy_mode", tags=["easy_mode"])
app.include_router(easy_mode.router, prefix="/api/easy-mode", tags=["easy-mode"])
app.include_router(streaming.router, prefix="/easy_mode", tags=["streaming"])
app.include_router(graph.router)
app.include_router(editor.router)


# 復元されたルーターの動的/静的登録
restored_routers = [
    "src.backend.routers.books",
    "src.backend.routers.plots",
    "src.backend.routers.episodes",
    "src.backend.routers.tasks",
    "src.backend.routers.patches",
    "src.backend.routers.issues",
    "src.backend.routers.marketing",
    "src.backend.routers.prompt_versions",
    "src.backend.routers.misc",
    "src.backend.routers.novel",
    "src.backend.routers.commercial",
    "src.backend.routers.illustrations",
]

for mod_path in restored_routers:
    try:
        mod = importlib.import_module(mod_path)
        if hasattr(mod, "router"):
            app.include_router(mod.router)
    except Exception as e:
        logger.warning(f"Could not load router {mod_path}: {e}")


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
