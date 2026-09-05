"""DAG Task and Dependency Graph Models (Step 35)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

TaskStatus = Literal["pending", "ready", "running", "completed", "failed", "cancelled"]


class TaskResourceRequirement(BaseModel):
    """Resource requirement for DAG worker scheduling."""

    cpu_cores: float = Field(default=1.0, description="Required CPU cores")
    gpu_mem_mb: int = Field(default=0, description="Required GPU VRAM in MB")
    ram_mb: int = Field(default=512, description="Required RAM in MB")


class DAGTaskNode(BaseModel):
    """A single node within the Directed Acyclic Graph."""

    task_id: str = Field(description="Unique task identifier")
    name: str = Field(default="", description="Human-readable task label")
    func_name: str = Field(description="Target function or agent name to execute")
    kwargs: dict[str, Any] = Field(default_factory=dict, description="Arguments passed to task function")
    dependencies: list[str] = Field(default_factory=list, description="List of parent task IDs")
    resources: TaskResourceRequirement = Field(default_factory=TaskResourceRequirement)
    priority: int = Field(default=0, description="Execution priority (higher executes earlier)")
    status: TaskStatus = Field(default="pending", description="Current execution state")
    retry_limit: int = Field(default=3, description="Max allowed retry attempts")
    retry_count: int = Field(default=0, description="Current retry attempt")
    result: Any = Field(default=None, description="Output returned by task execution")
    error: str | None = Field(default=None, description="Error message if failed")
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)


class DAGGraph(BaseModel):
    """Complete Directed Acyclic Graph structure."""

    dag_id: str = Field(description="Unique DAG workflow identifier")
    nodes: dict[str, DAGTaskNode] = Field(default_factory=dict, description="Lookup of task_id to node")

    def add_node(self, node: DAGTaskNode) -> None:
        """Add a task node to the DAG."""
        self.nodes[node.task_id] = node

    def add_dependency(self, child_id: str, parent_id: str) -> None:
        """Declare that child_id depends on parent_id completing first."""
        if child_id not in self.nodes:
            raise KeyError(f"Child task '{child_id}' not found in DAG")
        if parent_id not in self.nodes:
            raise KeyError(f"Parent task '{parent_id}' not found in DAG")
        if parent_id not in self.nodes[child_id].dependencies:
            self.nodes[child_id].dependencies.append(parent_id)

    def get_ready_tasks(self) -> list[DAGTaskNode]:
        """Return tasks that are ready to run (all parent dependencies are completed)."""
        ready = []
        for task in self.nodes.values():
            if task.status in ["pending", "ready"]:
                parents_done = all(
                    self.nodes[p_id].status == "completed"
                    for p_id in task.dependencies
                    if p_id in self.nodes
                )
                if parents_done:
                    task.status = "ready"
                    ready.append(task)
        # 優先度順にソート
        ready.sort(key=lambda t: t.priority, reverse=True)
        return ready

    def mark_running(self, task_id: str) -> None:
        """Mark task as running."""
        if task_id in self.nodes:
            self.nodes[task_id].status = "running"
            self.nodes[task_id].started_at = datetime.now()

    def mark_completed(self, task_id: str, result: Any = None) -> None:
        """Mark task as successfully completed."""
        if task_id in self.nodes:
            node = self.nodes[task_id]
            node.status = "completed"
            node.result = result
            node.completed_at = datetime.now()

    def mark_failed(self, task_id: str, error: str) -> None:
        """Mark task as failed."""
        if task_id in self.nodes:
            node = self.nodes[task_id]
            node.status = "failed"
            node.error = error
            node.completed_at = datetime.now()

    def is_all_completed(self) -> bool:
        """Check if all nodes have completed successfully."""
        return len(self.nodes) > 0 and all(n.status == "completed" for n in self.nodes.values())

    def has_failures(self) -> bool:
        """Check if any node has failed without recovery."""
        return any(n.status == "failed" for n in self.nodes.values())


__all__ = [
    "TaskStatus",
    "TaskResourceRequirement",
    "DAGTaskNode",
    "DAGGraph",
]
