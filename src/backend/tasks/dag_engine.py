"""DAG Cycle Detection & Topological Sort Engine (Step 36)."""
from __future__ import annotations

from collections import deque
from typing import Dict, List, Set

from src.backend.tasks.dag_models import DAGGraph, DAGTaskNode


class DAGCycleError(ValueError):
    """Raised when a circular dependency is detected in the DAG."""
    pass


class DAGEngine:
    """Provides validation, cycle detection, and topological sorting for DAGGraph."""

    @staticmethod
    def validate_dag(graph: DAGGraph) -> bool:
        """Validate that all referenced dependencies exist and graph has no cycles."""
        for task_id, node in graph.nodes.items():
            for dep_id in node.dependencies:
                if dep_id not in graph.nodes:
                    raise KeyError(
                        f"Task '{task_id}' depends on non-existent task '{dep_id}'"
                    )
        DAGEngine.topological_sort(graph)
        return True

    @staticmethod
    def topological_sort(graph: DAGGraph) -> list[str]:
        """Perform Kahn's algorithm to find a valid execution order.

        Raises:
            DAGCycleError: If a circular dependency exists.
        """
        nodes = graph.nodes
        if not nodes:
            return []

        # 入次数（依存している親の数）を計算
        # edge: parent -> child
        in_degree: dict[str, int] = {t_id: 0 for t_id in nodes}
        dependents: dict[str, list[str]] = {t_id: [] for t_id in nodes}

        for t_id, node in nodes.items():
            in_degree[t_id] = len(node.dependencies)
            for dep in node.dependencies:
                if dep in dependents:
                    dependents[dep].append(t_id)

        # 入次数 0 のノードをキューに追加
        queue: deque[str] = deque([
            t_id for t_id, deg in in_degree.items() if deg == 0
        ])
        sorted_order: list[str] = []

        while queue:
            curr = queue.popleft()
            sorted_order.append(curr)

            for child in dependents.get(curr, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        # 全ノードが処理されていなければ循環が存在する
        if len(sorted_order) != len(nodes):
            cycle_candidates = [t_id for t_id, deg in in_degree.items() if deg > 0]
            raise DAGCycleError(
                f"Circular dependency detected involving tasks: {cycle_candidates}"
            )

        return sorted_order

    @staticmethod
    def get_execution_stages(graph: DAGGraph) -> list[list[str]]:
        """Group tasks into parallelizable stages.

        Stage 0 can run immediately.
        Stage N can run once all tasks in Stages 0..N-1 on which it depends are done.
        """
        DAGEngine.validate_dag(graph)
        nodes = graph.nodes
        if not nodes:
            return []

        task_depth: dict[str, int] = {}
        sorted_order = DAGEngine.topological_sort(graph)

        for t_id in sorted_order:
            node = nodes[t_id]
            if not node.dependencies:
                task_depth[t_id] = 0
            else:
                max_parent_depth = max(
                    task_depth.get(dep, 0) for dep in node.dependencies if dep in task_depth
                )
                task_depth[t_id] = max_parent_depth + 1

        max_depth = max(task_depth.values()) if task_depth else 0
        stages: list[list[str]] = [[] for _ in range(max_depth + 1)]

        for t_id, depth in task_depth.items():
            stages[depth].append(t_id)

        # 各ステージ内を優先度順でソート
        for stage in stages:
            stage.sort(key=lambda tid: nodes[tid].priority, reverse=True)

        return stages


__all__ = ["DAGCycleError", "DAGEngine"]
