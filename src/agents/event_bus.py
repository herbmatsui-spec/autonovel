# src/agents/event_bus.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable
import asyncio


@dataclass
class AgentEvent:
    agent: str
    payload: dict[str, Any]
    correlation_id: str


class EventBus:
    def __init__(self, use_redis: bool = False):
        self._subs: dict[str, list[Callable[[AgentEvent], Awaitable[None]]]] = {}
        self._redis = None
        self._use_redis = use_redis

    def subscribe(self, agent: str, handler: Callable[[AgentEvent], Awaitable[None]]) -> None:
        self._subs.setdefault(agent, []).append(handler)

    async def publish(self, event: AgentEvent) -> None:
        for handler in self._subs.get(event.agent, []):
            asyncio.create_task(handler(event))
        # Redis Stream への投入は use_redis=True 時に実装