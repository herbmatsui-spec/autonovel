# src/agents/orchestrator.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

from src.agents.event_bus import AgentEvent, EventBus


class AgentName(str, Enum):
    PLANNING = "planning"
    PLOT = "plot"
    BIBLE = "bible"
    CONTEXT_BUILDER = "context_builder"
    WRITING = "writing"
    AUDIT = "audit"
    ILLUSTRATION = "illustration"
    MARKETING = "marketing"


@dataclass
class AgentContext:
    book_id: int
    branch_id: int
    ep_num: int
    artifacts: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    next_agent: AgentName | None
    artifacts: dict[str, Any]
    should_retry: bool = False
    error: str | None = None


AgentNode = Callable[[AgentContext], Awaitable[AgentResult]]


class Orchestrator:
    def __init__(
        self,
        nodes: dict[AgentName, AgentNode],
        event_bus: Optional[EventBus] = None,
        correlation_id: Optional[str] = None,
    ):
        self.nodes = nodes
        self.event_bus = event_bus
        self.correlation_id = correlation_id or "unknown"

    async def run(self, ctx: AgentContext, start: AgentName) -> AgentContext:
        current = start
        while current:
            # ノード実行前イベント発行
            if self.event_bus:
                await self.event_bus.publish(
                    AgentEvent(
                        agent=current.value,
                        payload={"status": "started", "ep_num": ctx.ep_num},
                        correlation_id=self.correlation_id,
                    )
                )

            node = self.nodes.get(current)
            if node is None:
                raise RuntimeError(f"Agent node not registered: {current.value}")

            result = await node(ctx)
            ctx.artifacts.update(result.artifacts)

            # ノード実行後イベント発行
            if self.event_bus:
                await self.event_bus.publish(
                    AgentEvent(
                        agent=current.value,
                        payload={
                            "status": "completed" if not result.error else "failed",
                            "ep_num": ctx.ep_num,
                            "next_agent": result.next_agent.value if result.next_agent else None,
                            "should_retry": result.should_retry,
                            "error": result.error,
                        },
                        correlation_id=self.correlation_id,
                    )
                )

            if result.should_retry:
                continue
            if result.error:
                raise RuntimeError(f"{current.value}: {result.error}")
            current = result.next_agent
        return ctx
