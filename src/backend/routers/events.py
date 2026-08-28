"""
src/backend/routers/events.py - リアルタイムSSEイベント配信エンドポイント
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from src.backend.auth import get_api_key_service
from src.backend.sse_manager import get_sse_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("/stream")
async def event_stream(
    # ブラウザの EventSource は標準でヘッダ指定が難しいためクエリパラメータの api_key も許容
    api_key: Optional[str] = Query(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    リアルタイムイベント配信用 SSE ストリームエンドポイント。
    エージェントの思考プロセス、推敲ログ、全体進捗率をリアルタイムに配信します。
    """
    service = get_api_key_service()
    if not service.disabled:
        key = api_key or x_api_key
        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error_code": "UNAUTHORIZED", "error_message": "API キーが指定されていません。"},
            )
        if not service.validate(key):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error_code": "FORBIDDEN", "error_message": "API キーが無効です。"},
            )

    logger.info("[EventsRouter] New authenticated SSE connection request received.")
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
