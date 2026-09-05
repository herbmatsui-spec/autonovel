"""DAG-Based Hybrid Batch Scheduler (Steps 38-42)."""
from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set

from src.backend.tasks.dag_models import (
    DAGGraph,
    DAGTaskNode,
    TaskResourceRequirement,
    TaskStatus,
)
from src.backend.tasks.dag_engine import DAGEngine, DAGCycleError
from src.backend.tasks.resource_manager import ResourceManager

logger = logging.getLogger(__name__)


class DAGScheduler:
    """Orchestrates parallel execution of DAG tasks with resource monitoring and fine-grained recovery."""

    def __init__(
        self,
        resource_manager: ResourceManager | None = None,
        huey_instance: Any = None,
        task_registry: dict[str, Callable] | None = None,
    ) -> None:
        self.resource_manager = resource_manager or ResourceManager()
        self.huey_instance = huey_instance
        self.task_registry: dict[str, Callable] = task_registry or {}
        self.worker_affinity_map: dict[str, str] = {}  # chapter_key -> worker_id (Step 40)
        self.active_allocations = TaskResourceRequirement(cpu_cores=0.0, ram_mb=0, gpu_mem_mb=0)

    def register_task(self, name: str, fn: Callable) -> None:
        """Register a callable function for a given func_name."""
        self.task_registry[name] = fn

    async def run_dag(
        self,
        graph: DAGGraph,
        max_concurrency: int | None = None,
        poll_interval: float = 0.05,
    ) -> DAGGraph:
        """Execute all nodes in the DAG respecting dependencies, resources, and affinity.

        (Steps 38, 39, 40, 41)
        """
        DAGEngine.validate_dag(graph)

        limits = self.resource_manager.calculate_worker_pool_limits()
        effective_max = max_concurrency or limits["max_parallel_tasks"]

        running_tasks: dict[str, asyncio.Task] = {}
        allocated_resources: dict[str, TaskResourceRequirement] = {}

        while not graph.is_all_completed():
            # 障害発生かつリカバリ不能な場合の早期中断チェック
            if graph.has_failures():
                logger.error(f"DAG {graph.dag_id} contains fatal task failures, halting.")
                break

            # 準備完了タスクの取得 (Step 39)
            ready_tasks = graph.get_ready_tasks()

            # アフィニティ並び替え (Step 40: 同一章タスクを優先)
            ready_tasks = self._sort_by_affinity(ready_tasks)

            for task_node in ready_tasks:
                if len(running_tasks) >= effective_max:
                    break

                req = task_node.resources
                if not self.resource_manager.can_schedule(req, self.active_allocations):
                    continue

                # リソース確保
                self._allocate_resources(task_node.task_id, req, allocated_resources)
                graph.mark_running(task_node.task_id)

                # 非同期タスクとして起動
                coro = self._execute_task_wrapper(graph, task_node)
                t = asyncio.create_task(coro)
                running_tasks[task_node.task_id] = t

            if not running_tasks and not ready_tasks:
                # 依存待ちか完了
                if graph.is_all_completed() or graph.has_failures():
                    break
                await asyncio.sleep(poll_interval)
                continue

            # デッドロック防止: 実行中タスクが0件なのに ready_tasks がリソース制約で開始できない場合、最優先タスクを強制開始
            if not running_tasks and ready_tasks:
                forced_node = ready_tasks[0]
                req = forced_node.resources
                self._allocate_resources(forced_node.task_id, req, allocated_resources)
                graph.mark_running(forced_node.task_id)
                coro = self._execute_task_wrapper(graph, forced_node)
                t = asyncio.create_task(coro)
                running_tasks[forced_node.task_id] = t

            # 実行中タスクの完了を待機
            if running_tasks:
                done, _ = await asyncio.wait(
                    running_tasks.values(),
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=poll_interval,
                )
                # 完了タスクのクリーンアップ
                finished_ids = [
                    tid for tid, task in running_tasks.items() if task in done
                ]
                for fid in finished_ids:
                    running_tasks.pop(fid, None)
                    self._release_resources(fid, allocated_resources)

        return graph

    async def _execute_task_wrapper(self, graph: DAGGraph, task_node: DAGTaskNode) -> None:
        """Wrapper to execute task function and handle retries/failures (Step 42)."""
        fn = self.task_registry.get(task_node.func_name)
        if not fn:
            graph.mark_failed(task_node.task_id, f"Function '{task_node.func_name}' not registered")
            return

        # アフィニティワーカーのバインド (Step 40)
        chapter_key = f"{task_node.kwargs.get('book_id', 0)}:{task_node.kwargs.get('ep_num', 0)}"
        worker_id = self.worker_affinity_map.get(chapter_key) or f"worker_{task_node.task_id}"
        self.worker_affinity_map[chapter_key] = worker_id

        try:
            res = fn(**task_node.kwargs)
            if inspect.iscoroutine(res):
                res = await res
            graph.mark_completed(task_node.task_id, result=res)
            logger.info(f"Task '{task_node.task_id}' completed on {worker_id}")
        except Exception as exc:
            logger.warning(f"Task '{task_node.task_id}' failed: {exc}")
            # リトライ制御 (Step 42)
            task_node.retry_count += 1
            if task_node.retry_count <= task_node.retry_limit:
                logger.info(f"Retrying task '{task_node.task_id}' (attempt {task_node.retry_count}/{task_node.retry_limit})")
                task_node.status = "ready"
            else:
                graph.mark_failed(task_node.task_id, str(exc))

    def retry_failed_subgraph(self, graph: DAGGraph, failed_task_id: str) -> list[str]:
        """Step 42: Fine-grained recovery. Resets only the failed task and its downstream dependencies.

        Upstream succeeded tasks (e.g. plot generation, writing) are kept completed.
        """
        if failed_task_id not in graph.nodes:
            raise KeyError(f"Task '{failed_task_id}' not found in DAG")

        # 下流タスク（このタスクに依存している全ノード）をBFSで収集
        downstream: set[str] = {failed_task_id}
        queue = [failed_task_id]

        while queue:
            curr = queue.pop(0)
            for tid, node in graph.nodes.items():
                if curr in node.dependencies and tid not in downstream:
                    downstream.add(tid)
                    queue.append(tid)

        # 収集したノードのみリセット
        for tid in downstream:
            node = graph.nodes[tid]
            node.status = "pending" if tid != failed_task_id else "ready"
            node.error = None
            node.retry_count = 0
            node.result = None

        logger.info(f"Reset {len(downstream)} downstream tasks for recovery: {downstream}")
        return sorted(list(downstream))

    def _sort_by_affinity(self, ready_tasks: list[DAGTaskNode]) -> list[DAGTaskNode]:
        """Step 40: Sort ready tasks so tasks with existing worker affinity run first."""
        def affinity_key(task: DAGTaskNode) -> int:
            chapter_key = f"{task.kwargs.get('book_id', 0)}:{task.kwargs.get('ep_num', 0)}"
            return 1 if chapter_key in self.worker_affinity_map else 0

        # アフィニティありを優先、次に priority 降順
        return sorted(ready_tasks, key=lambda t: (affinity_key(t), t.priority), reverse=True)

    def _allocate_resources(
        self,
        task_id: str,
        req: TaskResourceRequirement,
        allocated_map: dict[str, TaskResourceRequirement],
    ) -> None:
        allocated_map[task_id] = req
        self.active_allocations.cpu_cores += req.cpu_cores
        self.active_allocations.ram_mb += req.ram_mb
        self.active_allocations.gpu_mem_mb += req.gpu_mem_mb

    def _release_resources(
        self,
        task_id: str,
        allocated_map: dict[str, TaskResourceRequirement],
    ) -> None:
        req = allocated_map.pop(task_id, None)
        if req:
            self.active_allocations.cpu_cores = max(0.0, self.active_allocations.cpu_cores - req.cpu_cores)
            self.active_allocations.ram_mb = max(0, self.active_allocations.ram_mb - req.ram_mb)
            self.active_allocations.gpu_mem_mb = max(0, self.active_allocations.gpu_mem_mb - req.gpu_mem_mb)


__all__ = ["DAGScheduler"]
