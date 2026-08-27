"""
src/backend/routers/events.py - リアルタイムSSEイベント配信エンドポイント
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from src.backend.auth import require_api_key
from src.backend.sse_manager import get_sse_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("/stream")
async def event_stream(
    # ブラウザの EventSource は標準でヘッダ指定が難しいためクエリパラメータの api_key も許容
    api_key: Optional[str] = Query(None),
):
    """
    リアルタイムイベント配信用 SSE ストリームエンドポイント。
    エージェントの思考プロセス、推敲ログ、全体進捗率をリアルタイムに配信します。
    """
    logger.info("[EventsRouter] New SSE connection request received.")
    sse_manager = get_sse_manager()
    queue = await sse_manager.register()

    return StreamingResponse(
        sse_manager.event_generator(queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginxのリバースプロキシバッファリングを無効化
        },
    )
