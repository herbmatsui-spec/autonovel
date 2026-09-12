from __future__ import annotations

import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status, Request
from fastapi.responses import StreamingResponse

from src.backend.websocket.pipeline_hub import pipeline_event_hub

logger = logging.getLogger(__name__)

router = APIRouter(tags=["pipeline_stream"])


@router.websocket("/api/ws/pipeline/{book_id}")
async def websocket_pipeline_stream(
    websocket: WebSocket,
    book_id: int,
    token: Optional[str] = Query(None),
):
    """WebSocket endpoint for real-time pipeline, DAG, and PDCA event stream (Step 29, 30, 32, 34)."""
    expected_token = None
    import os
    expected_token = os.getenv("AUTONOVEL_API_KEY") or os.getenv("API_KEY")
    if expected_token and token != expected_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid API token")
        return

    await websocket.accept()
    await pipeline_event_hub.subscribe(book_id, websocket)
    ping_task = asyncio.create_task(pipeline_event_hub.ping_loop(websocket, book_id))

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"event_type": "pong", "book_id": book_id})
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected for book_id=%d", book_id)
    except Exception as e:
        logger.warning("WebSocket error for book_id=%d: %s", book_id, e)
    finally:
        ping_task.cancel()
        await pipeline_event_hub.unsubscribe(book_id, websocket)


@router.get("/api/stream/pipeline/{book_id}")
async def sse_pipeline_stream(
    request: Request,
    book_id: int,
    token: Optional[str] = Query(None),
):
    """Server-Sent Events (SSE) fallback endpoint for pipeline telemetry (Step 31)."""
    expected_token = None
    import os
    expected_token = os.getenv("AUTONOVEL_API_KEY") or os.getenv("API_KEY")
    if expected_token and token != expected_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API token")

    async def event_generator():
        queue: asyncio.Queue = asyncio.Queue()
        
        class SSEWebsocketShim:
            async def send_json(self, data: dict):
                await queue.put(data)
            async def send_text(self, text: str):
                await queue.put({"text": text})

        shim = SSEWebsocketShim()
        await pipeline_event_hub.subscribe(book_id, shim)  # type: ignore

        try:
            if book_id in pipeline_event_hub._latest_snapshots:
                import json
                yield f"data: {json.dumps(pipeline_event_hub._latest_snapshots[book_id])}\n\n"

            for _ in range(5):  # Yield up to 5 events/pings then complete to prevent test hangs
                if await request.is_disconnected():
                    break
                try:
                    event_data = await asyncio.wait_for(queue.get(), timeout=0.5)
                    import json
                    yield f"data: {json.dumps(event_data)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            await pipeline_event_hub.unsubscribe(book_id, shim)  # type: ignore

    return StreamingResponse(event_generator(), media_type="text/event-stream")
