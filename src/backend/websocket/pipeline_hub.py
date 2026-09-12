import asyncio
import logging
from datetime import datetime
from typing import Set, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
from src.backend.schemas.pipeline_events import PipelineEvent

logger = logging.getLogger(__name__)

class PipelineEventHub:
    def __init__(self):
        # book_id -> set of WebSocket connections or queues
        self._subscribers: Dict[int, Set[WebSocket]] = {}
        # book_id -> latest event snapshot
        self._latest_snapshots: Dict[int, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, book_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            if book_id not in self._subscribers:
                self._subscribers[book_id] = set()
            self._subscribers[book_id].add(websocket)
            
            # Send latest snapshot if available
            if book_id in self._latest_snapshots:
                try:
                    await websocket.send_json(self._latest_snapshots[book_id])
                except Exception as e:
                    logger.warning(f"Failed to send initial snapshot to subscriber: {e}")

    async def unsubscribe(self, book_id: int, websocket: WebSocket) -> None:
        async with self._lock:
            if book_id in self._subscribers:
                self._subscribers[book_id].discard(websocket)
                if not self._subscribers[book_id]:
                    del self._subscribers[book_id]

    async def broadcast(self, event: PipelineEvent) -> None:
        async with self._lock:
            self._latest_snapshots[event.book_id] = {
                "event_type": event.event_type,
                "book_id": event.book_id,
                "task_id": event.task_id,
                "timestamp": event.timestamp,
                "payload": event.payload,
            }
            if event.book_id not in self._subscribers:
                return
            websockets = list(self._subscribers[event.book_id])

        disconnected = []
        event_data = {
            "event_type": event.event_type,
            "book_id": event.book_id,
            "task_id": event.task_id,
            "timestamp": event.timestamp,
            "payload": event.payload,
        }

        for ws in websockets:
            try:
                await ws.send_json(event_data)
            except Exception as e:
                logger.warning(f"WebSocket send error, removing subscriber: {e}")
                disconnected.append(ws)

        if disconnected:
            async with self._lock:
                if event.book_id in self._subscribers:
                    for ws in disconnected:
                        self._subscribers[event.book_id].discard(ws)

    async def ping_loop(self, websocket: WebSocket, book_id: int, interval: float = 30.0) -> None:
        """Heartbeat ping/pong loop to keep connection alive and detect dead connections."""
        try:
            while True:
                await asyncio.sleep(interval)
                await websocket.send_json({"event_type": "ping", "book_id": book_id, "timestamp": datetime.now().isoformat() if 'datetime' in globals() else ""})
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

pipeline_event_hub = PipelineEventHub()
