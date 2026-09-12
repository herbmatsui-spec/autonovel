import asyncio
from collections import defaultdict
from typing import Any

from src.backend.schemas.pipeline_events import PipelineEvent


class PipelineEventHub:
    def __init__(self):
        self._subscribers: dict[int, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, book_id: int, queue: asyncio.Queue) -> None:
        self._subscribers[book_id].append(queue)

    def unsubscribe(self, book_id: int, queue: asyncio.Queue) -> None:
        if book_id in self._subscribers:
            try:
                self._subscribers[book_id].remove(queue)
            except ValueError:
                pass
            if not self._subscribers[book_id]:
                del self._subscribers[book_id]

    async def broadcast(self, event: PipelineEvent) -> None:
        book_id = event.book_id
        if book_id not in self._subscribers:
            return
        dead_queues = []
        for queue in self._subscribers[book_id]:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(queue)
        for queue in dead_queues:
            self.unsubscribe(book_id, queue)