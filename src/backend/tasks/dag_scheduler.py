"""DAG-Based Hybrid Batch Scheduler (Steps 38-42)."""
from __future__ import annotations

import asyncio
import inspect
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set

from src.backend.tasks.scheduling_policies import SchedulingPolicy, AffinityPriorityPolicy
from src.backend.tasks.metrics_collector import MetricsCollector, NoOpMetricsCollector, TaskMetrics
from src.backend.tasks.dag_persistence import DAGPersistence, FileSystemDAGPersistence

from src.backend.tasks.dag_models import (
    DAGGraph,
    DAGTaskNode,
    TaskResourceRequirement,
    TaskStatus,
)
from src.backend.tasks.dag_engine import DAGEngine, DAGCycleError
from src.backend.tasks.resource_manager import ResourceManager

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _ResourceSemaphores:
    cpu: asyncio.Semaphore
    ram: asyncio.Semaphore
    gpu: asyncio.Semaphore


class DAGScheduler:
    """Orchestrates parallel execution of DAG tasks with resource monitoring and fine-grained recovery."""

    def __init__(
        self,
        resource_manager: ResourceManager | None = None,
        huey_instance: Any = None,
        task_registry: dict[str, Callable] | None = None,
        scheduling_policy: SchedulingPolicy | None = None,
        metrics_collector: MetricsCollector | None = None,
        persistence: DAGPersistence | None = None,
        checkpoint_interval: int = 5,  # N タスク完了ごと
    ) -> None:
        self.resource_manager = resource_manager or ResourceManager()
        self.huey_instance = huey_instance
        self.task_registry: dict[str, Callable] = task_registry or {}
        self.worker_affinity_map: dict[str, str] = {}  # chapter_key -> worker_id (Step 40)
        self.active_allocations = TaskResourceRequirement(cpu_cores=0.0, ram_mb=0, gpu_mem_mb=0)

        # Pluggable scheduling policy (Step 3)
        self.scheduling_policy = scheduling_policy or AffinityPriorityPolicy(self.worker_affinity_map)

        # Metrics collector (Step 4)
        self.metrics = metrics_collector or NoOpMetricsCollector()

        # Checkpoint persistence (Step 6)
        self.persistence = persistence or FileSystemDAGPersistence()
        self.checkpoint_interval = checkpoint_interval
        self._tasks_since_checkpoint = 0

        # Resource semaphores for backpressure (Step 1+2)
        limits = self.resource_manager.calculate_worker_pool_limits()
        max_parallel = limits["max_parallel_tasks"]
        ram_slots = max(1, int(self.resource_manager.get_available_ram_mb() * self.resource_manager.max_ram_ratio // 512))
        gpu_slots = limits["image_workers"]

        self._semaphores = _ResourceSemaphores(
            cpu=asyncio.Semaphore(max_parallel),
            ram=asyncio.Semaphore(ram_slots),
            gpu=asyncio.Semaphore(gpu_slots),
        )
        self._poll_interval = 0.05
        self._max_poll_interval = 1.0

    def register_task(self, name: str, fn: Callable) -> None:
        """Register a callable function for a given func_name."""
        self.task_registry[name] = fn

    async def run_dag(
        self,
        graph: DAGGraph | None = None,
        max_concurrency: int | None = None,
        poll_interval: float = 0.05,
        resume_from: str | None = None,
    ) -> DAGGraph:
        """Execute all nodes in the DAG respecting dependencies, resources, and affinity.

        Uses asyncio.TaskGroup for structured concurrency and semaphores for backpressure.
        
        Args:
            graph: DAGGraph to execute. Optional if resume_from is provided.
            max_concurrency: Maximum parallel tasks.
            poll_interval: Polling interval in seconds.
            resume_from: Checkpoint ID to resume from. If provided, graph is loaded from checkpoint.
        """
        # Resume from checkpoint
        if resume_from:
            loaded = self.persistence.load_checkpoint(resume_from)
            if not loaded:
                raise ValueError(f"Checkpoint not found: {resume_from}")
            graph = loaded
            logger.info(f"Resumed from checkpoint: {resume_from}")
        elif graph is None:
            raise ValueError("Either graph or resume_from must be provided")

        DAGEngine.validate_dag(graph)

        limits = self.resource_manager.calculate_worker_pool_limits()
        effective_max = max_concurrency or limits["max_parallel_tasks"]

        allocated_resources: dict[str, TaskResourceRequirement] = {}
        self._poll_interval = poll_interval
        self._max_poll_interval = max(1.0, poll_interval * 20)
        current_poll = poll_interval
        self._tasks_since_checkpoint = 0  # Reset checkpoint counter

        try:
            async with asyncio.TaskGroup() as tg:
                while not graph.is_all_completed():
                    # Fatal failure check
                    if graph.has_failures():
                        logger.error(f"DAG {graph.dag_id} contains fatal task failures, halting.")
                        break

                    ready_tasks = graph.get_ready_tasks()
                    ready_tasks = self._sort_by_affinity(ready_tasks)

                    launched = 0
                    for task_node in ready_tasks:
                        req = task_node.resources
                        if not self._can_schedule_approx(req):
                            continue

                        # Acquire semaphores (blocks = backpressure)
                        await self._acquire_resources(req)

                        self._allocate_resources(task_node.task_id, req, allocated_resources)
                        graph.mark_running(task_node.task_id)

                        coro = self._execute_task_wrapper(graph, task_node)
                        task = tg.create_task(coro)
                        task.add_done_callback(self._make_task_done_callback(task_node.task_id, allocated_resources, graph))

                        launched += 1

                    # Metrics: record queue depth and resource utilization
                    self._record_metrics(graph)

                    if launched == 0 and not ready_tasks:
                        # Waiting for dependencies or completed
                        if graph.is_all_completed() or graph.has_failures():
                            break
                        await asyncio.sleep(current_poll)
                        current_poll = min(current_poll * 1.5, self._max_poll_interval)
                        continue

                    # Yield to event loop so launched tasks can run
                    await asyncio.sleep(0)

                    # Reset poll interval when we launched something
                    current_poll = poll_interval

        except* Exception as eg:
            for exc in eg.exceptions:
                logger.exception(f"DAG execution failed: {exc}")
            raise

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

        # NUMA アフィニティ適用 (Linuxのみ, Step 5)
        if hasattr(os, 'sched_setaffinity') and self.resource_manager.numa_topology.numa_nodes:
            try:
                worker_idx = int(worker_id.split("_")[-1])
            except ValueError:
                worker_idx = 0
            
            is_gpu = task_node.resources.gpu_mem_mb > 0
            numa = self.resource_manager.get_worker_numa_affinity(worker_idx, is_gpu)
            
            if numa is not None:
                cpus = self.resource_manager.numa_topology.get_cpus_for_numa(numa)
                if cpus:
                    os.sched_setaffinity(0, cpus)  # 現在プロセスの CPU アフィニティ設定
                    logger.debug(f"Task {task_node.task_id} pinned to NUMA {numa} CPUs {cpus}")

        # Metrics: record task start
        start_time = time.monotonic()
        self.metrics.record_task_start(task_node.task_id, graph.dag_id, worker_id)

        try:
            res = fn(**task_node.kwargs)
            if inspect.iscoroutine(res):
                res = await res
            graph.mark_completed(task_node.task_id, result=res)
            logger.info(f"Task '{task_node.task_id}' completed on {worker_id}")
            
            # Metrics: record task end (success)
            duration = time.monotonic() - start_time
            self.metrics.record_task_end(TaskMetrics(
                task_id=task_node.task_id,
                dag_id=graph.dag_id,
                duration_seconds=duration,
                status="completed",
                retry_count=task_node.retry_count,
                worker_id=worker_id,
                resource_usage={
                    "cpu": task_node.resources.cpu_cores,
                    "ram": task_node.resources.ram_mb,
                    "gpu": task_node.resources.gpu_mem_mb,
                }
            ))
        except Exception as exc:
            logger.warning(f"Task '{task_node.task_id}' failed: {exc}")
            # リトライ制御 (Step 42)
            task_node.retry_count += 1
            if task_node.retry_count <= task_node.retry_limit:
                logger.info(f"Retrying task '{task_node.task_id}' (attempt {task_node.retry_count}/{task_node.retry_limit})")
                task_node.status = "ready"
                # Metrics: record retry
                self.metrics.record_retry(task_node.task_id, task_node.retry_count)
            else:
                graph.mark_failed(task_node.task_id, str(exc))
                # Metrics: record task end (failure)
                duration = time.monotonic() - start_time
                self.metrics.record_task_end(TaskMetrics(
                    task_id=task_node.task_id,
                    dag_id=graph.dag_id,
                    duration_seconds=duration,
                    status="failed",
                    retry_count=task_node.retry_count,
                    worker_id=worker_id,
                    resource_usage={}
                ))

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
        """Delegate to pluggable scheduling policy."""
        return self.scheduling_policy.sort_ready_tasks(ready_tasks)

    def set_scheduling_policy(self, policy: SchedulingPolicy) -> None:
        """実行中にスケジューリングポリシーを切り替える。"""
        self.scheduling_policy = policy
        logger.info(f"Scheduling policy changed to {type(policy).__name__}")

    def _record_metrics(self, graph: DAGGraph) -> None:
        """Record queue depth and resource utilization metrics."""
        # Queue depth
        ready = sum(1 for n in graph.nodes.values() if n.status == "ready")
        running = sum(1 for n in graph.nodes.values() if n.status == "running")
        pending = sum(1 for n in graph.nodes.values() if n.status == "pending")
        self.metrics.record_queue_depth(graph.dag_id, ready, running, pending)

        # Resource utilization
        avail = self.resource_manager.get_available_resources()
        if avail.cpu_cores > 0:
            cpu_pct = (self.active_allocations.cpu_cores / avail.cpu_cores) * 100
        else:
            cpu_pct = 0.0
        if avail.ram_mb > 0:
            ram_pct = (self.active_allocations.ram_mb / avail.ram_mb) * 100
        else:
            ram_pct = 0.0
        if avail.gpu_mem_mb > 0:
            gpu_pct = (self.active_allocations.gpu_mem_mb / avail.gpu_mem_mb) * 100
        else:
            gpu_pct = 0.0
        self.metrics.record_resource_utilization(cpu_pct, ram_pct, gpu_pct)

    def _allocate_resources(
        self,
        task_id: str,
        req: TaskResourceRequirement,
        allocated_map: dict[str, TaskResourceRequirement],
    ) -> None:
        """Track resource allocation for monitoring (semaphores handle actual limiting)."""
        allocated_map[task_id] = req
        self.active_allocations.cpu_cores += req.cpu_cores
        self.active_allocations.ram_mb += req.ram_mb
        self.active_allocations.gpu_mem_mb += req.gpu_mem_mb

    def _release_resources(
        self,
        task_id: str,
        allocated_map: dict[str, TaskResourceRequirement],
    ) -> None:
        """Release semaphores and update allocation tracking."""
        req = allocated_map.pop(task_id, None)
        if not req:
            return
        # Release semaphores in reverse order of acquisition
        if req.gpu_mem_mb > 0:
            self._semaphores.gpu.release()
        ram_slots = max(1, int(req.ram_mb / 512))
        for _ in range(ram_slots):
            self._semaphores.ram.release()
        self._semaphores.cpu.release()

        # Keep active_allocations updated for monitoring
        self.active_allocations.cpu_cores = max(0.0, self.active_allocations.cpu_cores - req.cpu_cores)
        self.active_allocations.ram_mb = max(0, self.active_allocations.ram_mb - req.ram_mb)
        self.active_allocations.gpu_mem_mb = max(0, self.active_allocations.gpu_mem_mb - req.gpu_mem_mb)

    async def _acquire_resources(self, req: TaskResourceRequirement) -> None:
        """Acquire semaphores for required resources. Fixed order prevents deadlock."""
        await self._semaphores.cpu.acquire()
        try:
            ram_slots = max(1, int(req.ram_mb / 512))
            for _ in range(ram_slots):
                await self._semaphores.ram.acquire()
            try:
                if req.gpu_mem_mb > 0:
                    await self._semaphores.gpu.acquire()
            except BaseException:
                for _ in range(ram_slots):
                    self._semaphores.ram.release()
                raise
        except BaseException:
            self._semaphores.cpu.release()
            raise

    def _make_task_done_callback(self, task_id: str, allocated_map: dict, graph: DAGGraph):
        """Create a done callback that releases resources and saves checkpoint."""
        def _done_callback(t: asyncio.Task) -> None:
            self._release_resources(task_id, allocated_map)
            self._tasks_since_checkpoint += 1
            if self._tasks_since_checkpoint >= self.checkpoint_interval:
                self._save_checkpoint(graph)
                self._tasks_since_checkpoint = 0
        return _done_callback

    def _save_checkpoint(self, graph: DAGGraph) -> None:
        """Save DAG state as checkpoint."""
        checkpoint_id = f"{graph.dag_id}_cp_{int(time.time())}"
        try:
            self.persistence.save_checkpoint(graph, checkpoint_id)
            logger.info(f"Checkpoint saved: {checkpoint_id}")
        except Exception as e:
            logger.warning(f"Checkpoint save failed: {e}")

    def find_latest_checkpoint(self, dag_id: str) -> Optional[str]:
        """指定 DAG の最新チェックポイント取得。"""
        checkpoints = self.persistence.list_checkpoints(dag_id)
        return checkpoints[-1] if checkpoints else None

    def auto_recover(self, dag_id: str) -> Optional[DAGGraph]:
        """最新チェックポイントから自動リカバリ。"""
        latest = self.find_latest_checkpoint(dag_id)
        if latest:
            return self.persistence.load_checkpoint(latest)
        return None

    def _can_schedule_approx(self, req: TaskResourceRequirement) -> bool:
        """Fast approximate check using semaphore current values."""
        if self._semaphores.cpu._value <= 0:
            return False
        ram_slots = max(1, int(req.ram_mb / 512))
        if self._semaphores.ram._value < ram_slots:
            return False
        if req.gpu_mem_mb > 0 and self._semaphores.gpu._value <= 0:
            return False
        return True

    async def _cancel_running_tasks(
        self,
        running_tasks: dict[str, asyncio.Task],
        allocated_resources: dict[str, TaskResourceRequirement],
    ) -> None:
        """Cancel all currently running asyncio tasks and release their allocated resources."""
        for tid, task in list(running_tasks.items()):
            if not task.done():
                task.cancel()
        if running_tasks:
            await asyncio.gather(*running_tasks.values(), return_exceptions=True)
            for tid in list(running_tasks.keys()):
                self._release_resources(tid, allocated_resources)
            running_tasks.clear()


__all__ = ["DAGScheduler"]
