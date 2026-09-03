# src/agents/orchestrator.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable


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
    def __init__(self, nodes: dict[AgentName, AgentNode]):
        self.nodes = nodes

    async def run(self, ctx: AgentContext, start: AgentName) -> AgentContext:
        current = start
        while current:
            node = self.nodes.get(current)
            if node is None:
                raise RuntimeError(f"Agent node not registered: {current.value}")
            result = await node(ctx)
            ctx.artifacts.update(result.artifacts)
            if result.should_retry:
                continue
            if result.error:
                raise RuntimeError(f"{current.value}: {result.error}")
            current = result.next_agent
        return ctx