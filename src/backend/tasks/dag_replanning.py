"""DAG Dynamic Replanning Engine (Phase 4 / Part 5).

Handles localized retries and safe cancellation of downstream tasks in a DAG
when chapter regeneration or audit failure is triggered by the closed-loop PDCA cycle.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Sequence

from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode, TaskStatus

logger = logging.getLogger(__name__)


@dataclass
class DAGReplanningState:
    """State snapshot of a DAG dynamic replanning event (Step 49)."""
    trigger_node_id: str
    affected_downstream_ids: list[str] = field(default_factory=list)
    cancelled_node_ids: list[str] = field(default_factory=list)
    rescheduled_node_ids: list[str] = field(default_factory=list)
    rollback_snapshots: dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_node_id": self.trigger_node_id,
            "affected_downstream_ids": list(self.affected_downstream_ids),
            "cancelled_node_ids": list(self.cancelled_node_ids),
            "rescheduled_node_ids": list(self.rescheduled_node_ids),
            "rollback_snapshots": self.rollback_snapshots,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


class DAGReplanner:
    """Orchestrates dynamic DAG dependency replanning, localized retries, and cascading cancellations."""

    @staticmethod
    def get_downstream_tasks(
        graph: DAGGraph,
        start_node_id: str,
        include_self: bool = False,
    ) -> list[str]:
        """Find all direct and indirect downstream dependent tasks via BFS (Step 50)."""
        if start_node_id not in graph.nodes:
            return []

        # Build reverse adjacency list: parent -> list of children
        children_map: dict[str, list[str]] = {nid: [] for nid in graph.nodes}
        for nid, node in graph.nodes.items():
            for parent_id in node.dependencies:
                if parent_id in children_map:
                    children_map[parent_id].append(nid)

        visited: set[str] = set()
        queue: deque[str] = deque([start_node_id])

        while queue:
            curr = queue.popleft()
            for child in children_map.get(curr, []):
                if child not in visited:
                    visited.add(child)
                    queue.append(child)

        downstream = list(visited)
        if include_self:
            downstream.insert(0, start_node_id)
        return downstream

    @classmethod
    def cancel_downstream_execution(
        cls,
        graph: DAGGraph,
        trigger_node_id: str,
        active_async_tasks: dict[str, asyncio.Task] | None = None,
    ) -> list[str]:
        """Safely cancel running and ready downstream tasks (Step 52)."""
        downstream = cls.get_downstream_tasks(graph, trigger_node_id, include_self=False)
        cancelled: list[str] = []

        for nid in downstream:
            node = graph.nodes.get(nid)
            if not node:
                continue

            if node.status in ["running", "ready", "pending"]:
                # Cancel running asyncio Task if handle provided
                if active_async_tasks and nid in active_async_tasks:
                    task = active_async_tasks[nid]
                    if not task.done():
                        task.cancel()
                        logger.info("Cancelled running async task %s due to replan of %s", nid, trigger_node_id)

                node.status = "cancelled"
                node.error = f"Cancelled due to upstream replanning of node '{trigger_node_id}'"
                cancelled.append(nid)

        return cancelled

    @classmethod
    def plan_local_retry(
        cls,
        graph: DAGGraph,
        target_node_id: str,
        new_kwargs: dict[str, Any] | None = None,
        reason: str = "PDCA regeneration request",
        active_async_tasks: dict[str, asyncio.Task] | None = None,
    ) -> DAGReplanningState:
        """Perform localized retry of target node and prepare downstream nodes for re-execution (Step 51-53)."""
        if target_node_id not in graph.nodes:
            raise KeyError(f"Target node '{target_node_id}' not found in DAG")

        target_node = graph.nodes[target_node_id]

        # 1. Cancel downstream tasks
        affected_downstream = cls.get_downstream_tasks(graph, target_node_id, include_self=False)
        cancelled = cls.cancel_downstream_execution(graph, target_node_id, active_async_tasks=active_async_tasks)

        # 2. Record rollback snapshots of original node states
        snapshots: dict[str, Any] = {
            target_node_id: {
                "status": target_node.status,
                "result": target_node.result,
                "retry_count": target_node.retry_count,
            }
        }
        for nid in affected_downstream:
            n = graph.nodes[nid]
            snapshots[nid] = {
                "status": n.status,
                "result": n.result,
            }

        # 3. Reset target node for retry
        target_node.status = "pending"
        target_node.retry_count += 1
        target_node.error = None
        if new_kwargs:
            target_node.kwargs.update(new_kwargs)

        # 4. Reset downstream nodes back to pending so they re-run once target completes
        rescheduled = [target_node_id]
        for nid in affected_downstream:
            node = graph.nodes[nid]
            node.status = "pending"
            node.result = None
            node.error = None
            rescheduled.append(nid)

        state = DAGReplanningState(
            trigger_node_id=target_node_id,
            affected_downstream_ids=affected_downstream,
            cancelled_node_ids=cancelled,
            rescheduled_node_ids=rescheduled,
            rollback_snapshots=snapshots,
            reason=reason,
        )

        logger.info(
            "DAGReplanner: replanned node %s (%d downstream reset: %s)",
            target_node_id,
            len(affected_downstream),
            affected_downstream,
        )
        return state


__all__ = [
    "DAGReplanningState",
    "DAGReplanner",
]
