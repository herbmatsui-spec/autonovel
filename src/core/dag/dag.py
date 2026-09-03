"""DAG Pipeline Implementation."""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional

from src.core.dag.context import PipelineContext

logger = logging.getLogger(__name__)


class DAGNode:
    """A single execution node in a DAG pipeline."""

    def __init__(self, name: str, handler: Optional[Callable[..., Any]] = None) -> None:
        self.name = name
        self.handler = handler

    async def execute(self, context: PipelineContext) -> None:
        if self.handler:
            res = self.handler(context)
            if hasattr(res, "__await__"):
                await res


class DAGPipeline:
    """DAG Pipeline managing execution of workflow nodes."""

    def __init__(self) -> None:
        self._nodes: List[DAGNode] = []

    def add_node(self, node: DAGNode) -> None:
        self._nodes.append(node)

    async def execute(self, context: Optional[PipelineContext] = None) -> None:
        ctx = context or PipelineContext()
        ctx.state = "running"
        for node in self._nodes:
            await node.execute(ctx)
        ctx.state = "completed"
