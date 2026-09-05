# src/agents/event_bus.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, List
import asyncio
import json
import redis.asyncio as redis


@dataclass
class AgentEvent:
    agent: str
    payload: dict[str, Any]
    correlation_id: str


# Phase 2: Specialist audit event types
AUDIT_SPECIALIST_STARTED = "audit.specialist.started"
AUDIT_SPECIALIST_COMPLETED = "audit.specialist.completed"

# Phase 4: Enrichment event types
ENRICHMENT_STARTED = "enrichment.started"
ENRICHMENT_STEP_COMPLETED = "enrichment.step_completed"
ENRICHMENT_COMPLETED = "enrichment.completed"
ENRICHMENT_ERROR = "enrichment.error"


class EventBus:
    def __init__(self, use_redis: bool = False, redis_url: Optional[str] = None):
        self._subs: dict[str, list[Callable[[AgentEvent], Awaitable[None]]]] = {}
        self._redis: Optional["redis.asyncio.Redis"] = None
        self._use_redis = use_redis
        self._redis_url = redis_url or "redis://localhost:6379/0"
        self._consumer_task: Optional[asyncio.Task] = None

    def subscribe(self, agent: str, handler: Callable[[AgentEvent], Awaitable[None]]) -> None:
        self._subs.setdefault(agent, []).append(handler)

    def subscribe_async(self, agent: str, handler: Callable[[AgentEvent], Awaitable[None]]) -> None:
        """非同期ハンドラ登録（subscribe のエイリアス）"""
        self.subscribe(agent, handler)

    async def publish(self, event: AgentEvent) -> List[asyncio.Task]:
        # ローカルハンドラ実行
        tasks = []
        for handler in self._subs.get(event.agent, []):
            tasks.append(asyncio.create_task(handler(event)))

        # Redis Stream へ発行
        if self._use_redis and self._redis is not None:
            stream_name = f"agent_events:{event.correlation_id}"
            tasks.append(asyncio.create_task(self._redis.xadd(
                stream_name,
                {
                    "agent": event.agent,
                    "payload": json.dumps(event.payload, ensure_ascii=False),
                    "correlation_id": event.correlation_id,
                },
            )))

        return tasks

    async def publish_async(self, event: AgentEvent) -> None:
        """非同期イベント発行（publish のエイリアス・戻り値無視）"""
        await self.publish(event)

    async def publish_sync(self, event: AgentEvent) -> None:
        """同期的にイベント発行（全ハンドラ完了を待つ）"""
        tasks = []
        for handler in self._subs.get(event.agent, []):
            tasks.append(asyncio.create_task(handler(event)))

        if self._use_redis and self._redis is not None:
            stream_name = f"agent_events:{event.correlation_id}"
            tasks.append(asyncio.create_task(self._redis.xadd(
                stream_name,
                {
                    "agent": event.agent,
                    "payload": json.dumps(event.payload, ensure_ascii=False),
                    "correlation_id": event.correlation_id,
                },
            )))

        if tasks:
            await asyncio.gather(*tasks)

    async def publish_blind(self, event: AgentEvent, gate: Any) -> List[asyncio.Task]:
        """Blind peer review 対応発行。
        
        gate.scrub_payload() で参照禁止エージェントの出力をマスクしてから発行する。
        """
        from src.services.blind_review import BlindReviewGate
        if isinstance(gate, BlindReviewGate):
            scrubbed_payload = gate.scrub_payload(event.payload)
            blind_event = AgentEvent(
                agent=event.agent,
                payload=scrubbed_payload,
                correlation_id=event.correlation_id,
            )
            return await self.publish(blind_event)
        return await self.publish(event)

    async def start_redis(self) -> None:
        """Redis 接続を初期化し、コンシューマータスクを開始。"""
        if not self._use_redis:
            return
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(self._redis_url, decode_responses=True)
            # コンシューマータスクは必要に応じて別途実装
        except ImportError:
            # redis-py 不在時は無視
            self._use_redis = False

    async def stop_redis(self) -> None:
        """Redis 接続をクローズ。"""
        if self._redis is not None:
            await self._redis.close()
            self._redis = None
        if self._consumer_task is not None:
            await self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass


__all__ = [
    "AgentEvent",
    "EventBus",
    "AUDIT_SPECIALIST_STARTED",
    "AUDIT_SPECIALIST_COMPLETED",
    "ENRICHMENT_STARTED",
    "ENRICHMENT_STEP_COMPLETED",
    "ENRICHMENT_COMPLETED",
    "ENRICHMENT_ERROR",
]