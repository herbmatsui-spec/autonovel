"""DAG-Based Hybrid Batch Scheduler (Steps 38-42)."""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from src.backend.tasks.scheduling_policies import SchedulingPolicy, AffinityPriorityPolicy
from src.backend.tasks.metrics_collector import MetricsCollector, NoOpMetricsCollector, TaskMetrics
from src.backend.tasks.dag_persistence import DAGPersistence, FileSystemDAGPersistence
from src.backend.tasks.worker_recovery import WorkerRecoveryManager

from src.backend.schemas.pipeline_events import PipelineEvent
    DAGGraph,
    DAGTaskNode,
    TaskResourceRequirement,
)
from src.backend.tasks.dag_engine import DAGEngine
from src.backend.tasks.resource_manager import ResourceManager
from src.backend.database.core import DatabaseManager

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
        checkpoint_interval: int = 5,
        use_huey: bool = False,
        event_bus: Any = None,
        replanner: Any = None,
        db_manager: DatabaseManager | None = None,
        worker_recovery: WorkerRecoveryManager | None = None,
        pipeline_event_hub: Any = None,
    ) -> None:
        self.resource_manager = resource_manager or ResourceManager()
        self.huey_instance = huey_instance
        self.task_registry: dict[str, Callable] = task_registry or {}
        self.worker_affinity_map: dict[str, str] = {}
        self.active_allocations = TaskResourceRequirement(cpu_cores=0.0, ram_mb=0, gpu_mem_mb=0)
        self.use_huey = use_huey
        self.event_bus = event_bus
        self.pipeline_event_hub = pipeline_event_hub
        self.db_manager = db_manager
        self.worker_recovery = worker_recovery

        # Dynamic replanning integration (Step 55)
        if replanner is None:
            try:
                from src.backend.tasks.dag_replanning import DAGReplanner
                self.replanner = DAGReplanner()
            except Exception:
                self.replanner = None
        else:
            self.replanner = replanner

        self.replanning_history: list[Any] = []
        self.active_async_tasks: dict[str, asyncio.Task] = {}

        # Pluggable scheduling policy (Step 3)
        self.scheduling_policy = scheduling_policy or AffinityPriorityPolicy(self.worker_affinity_map)

        # Metrics collector (Step 4)
        self.metrics = metrics_collector or NoOpMetricsCollector()

        # Checkpoint persistence (Step 6)
        self.persistence = persistence or FileSystemDAGPersistence()
        self.checkpoint_interval = checkpoint_interval
        self._tasks_since_checkpoint = 0

        # Resource semaphores for backpressure (lazy initialization in async loop)
        self._semaphores: _ResourceSemaphores | None = None
        self._poll_interval = 0.05
        self._max_poll_interval = 1.0

async def _publish_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Helper to publish DAG lifecycle events to EventBus (Step 55)."""
        if self.event_bus:
            try:
                if hasattr(self.event_bus, "publish_async"):
                    await self.event_bus.publish_async(event_type, payload)
                elif hasattr(self.event_bus, "publish"):
                    res = self.event_bus.publish(event_type, payload)
                    if inspect.iscoroutine(res):
                        await res
            except Exception as e:
                logger.debug(f"Failed to publish event {event_type}: {e}")
        
        # Also publish to PipelineEventHub for real-time WebSocket streaming
        if self.pipeline_event_hub:
            try:
                event = PipelineEvent(
                    event_type=event_type,
                    book_id=payload.get("book_id", 0),
                    task_id=payload.get("task_id", ""),
                    payload=payload,
                )
                await self.pipeline_event_hub.broadcast(event)
            except Exception as e:
                logger.debug(f"Failed to broadcast PipelineEvent {event_type}: {e}")

    def _init_semaphores(self) -> None:
        """Initialize semaphores lazily within the running event loop."""
        if self._semaphores is None:
            limits = self.resource_manager.calculate_worker_pool_limits()
            max_parallel = limits["max_parallel_tasks"]
            ram_slots = max(1, int(self.resource_manager.get_available_ram_mb() * self.resource_manager.max_ram_ratio // 512))
            gpu_slots = limits["image_workers"]
            self._semaphores = _ResourceSemaphores(
                cpu=asyncio.Semaphore(max_parallel),
                ram=asyncio.Semaphore(ram_slots),
                gpu=asyncio.Semaphore(gpu_slots),
            )

    def register_task(self, name: str, fn: Callable) -> None:
        """Register a callable function for a given func_name."""
        self.task_registry[name] = fn

    async def run_dag(
        self,
        graph: DAGGraph | None = None,
        max_concurrency: int | None = None,
        poll_interval: float = 0.05,
        resume_from: str | None = None,
        fail_fast: bool = False,
    ) -> DAGGraph:
        """Execute all nodes in the DAG respecting dependencies, resources, and affinity.

        Uses asyncio.TaskGroup for structured concurrency and semaphores for backpressure.
        
        Args:
            graph: DAGGraph to execute. Optional if resume_from is provided.
            max_concurrency: Maximum parallel tasks.
            poll_interval: Polling interval in seconds.
            resume_from: Checkpoint ID to resume from. If provided, graph is loaded from checkpoint.
            fail_fast: If True, halts immediately on first fatal task failure. If False, allows independent branches to complete.
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
        self._init_semaphores()

        try:
            async with asyncio.TaskGroup() as tg:
                while not graph.is_finished():
                    # Fatal failure check if fail_fast is enabled
                    if fail_fast and graph.has_failures():
                        logger.error(f"DAG {graph.dag_id} contains fatal task failures, halting (fail_fast=True).")
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
                        self.active_async_tasks[task_node.task_id] = task
                        task.add_done_callback(self._make_task_done_callback(task_node.task_id, allocated_resources, graph))

                        launched += 1

                    # Metrics: record queue depth and resource utilization
                    self._record_metrics(graph)

                    if launched == 0:
                        # Waiting for dependencies, waiting for resources, or all terminal
                        if graph.is_finished() or (fail_fast and graph.has_failures()):
                            break
                        await asyncio.sleep(current_poll)
                        current_poll = min(current_poll * 1.5, self._max_poll_interval)
                        continue

                    # Yield to event loop so launched tasks can run
                    await asyncio.sleep(0)

                    # Reset poll interval when we launched something
                    current_poll = poll_interval

            await self._publish_event("dag.completed", {
                "dag_id": graph.dag_id,
                "is_all_completed": graph.is_all_completed(),
                "is_finished": graph.is_finished(),
                "has_failures": graph.has_failures(),
            })

        except* Exception as eg:
            for exc in eg.exceptions:
                logger.exception(f"DAG execution failed: {exc}")
            raise
        finally:
            # Step 59: Ensure all allocated resources are released to prevent deadlocks
            for tid in list(allocated_resources.keys()):
                self._release_resources(tid, allocated_resources)

        return graph

    async def replan_node(
        self,
        graph: DAGGraph,
        target_node_id: str,
        new_kwargs: dict[str, Any] | None = None,
        reason: str = "PDCA regeneration request",
        max_replan_limit: int = 3,
    ) -> Any:
        """Dynamically replan a task node and safe-cancel/reschedule downstream tasks (Step 55-59)."""
        node = graph.nodes.get(target_node_id)
        if not node:
            raise KeyError(f"Node '{target_node_id}' not found in DAG")

        if self.replanner is None:
            from src.backend.tasks.dag_replanning import DAGReplanner
            self.replanner = DAGReplanner()

        # Step 57: Fail-safe limit check
        if node.retry_count >= max_replan_limit:
            err_msg = f"Exceeded max replan limit ({max_replan_limit}) for node '{target_node_id}'"
            logger.error(err_msg)
            graph.mark_failed(target_node_id, err_msg)
            graph.cascade_cancel_downstream(target_node_id, reason=err_msg)
            raise RuntimeError(err_msg)

        state = self.replanner.plan_local_retry(
            graph=graph,
            target_node_id=target_node_id,
            new_kwargs=new_kwargs,
            reason=reason,
            active_async_tasks=self.active_async_tasks,
        )

        self.replanning_history.append(state)

        # Step 59: Publish Event to EventBus
        await self._publish_event("dag.replanned", state.to_dict())
        return state

    def get_execution_summary(self, graph: DAGGraph) -> dict[str, Any]:
        """Step 56: Generate a complete execution summary and status of the DAG."""
        total_nodes = len(graph.nodes)
        status_counts = {"pending": 0, "ready": 0, "running": 0, "completed": 0, "failed": 0, "cancelled": 0}
        node_details = {}

        for tid, node in graph.nodes.items():
            status_counts[node.status] = status_counts.get(node.status, 0) + 1
            node_details[tid] = {
                "name": node.name,
                "status": node.status,
                "retry_count": node.retry_count,
                "started_at": node.started_at.isoformat() if node.started_at else None,
                "completed_at": node.completed_at.isoformat() if node.completed_at else None,
                "error": node.error,
                "has_result": node.result is not None,
            }

        progress_pct = (status_counts["completed"] / total_nodes * 100) if total_nodes > 0 else 0.0

        return {
            "dag_id": graph.dag_id,
            "total_nodes": total_nodes,
            "status_counts": status_counts,
            "progress_percent": round(progress_pct, 1),
            "is_all_completed": graph.is_all_completed(),
            "is_finished": graph.is_finished(),
            "has_failures": graph.has_failures(),
            "replanning_count": len(self.replanning_history),
            "total_rescheduled_tasks": sum(len(s.rescheduled_node_ids) for s in self.replanning_history),
            "nodes": node_details,
        }

    async def _execute_task_wrapper(self, graph: DAGGraph, task_node: DAGTaskNode) -> None:
        """Wrapper to execute task function (locally or via Huey) and handle retries/timeouts/failures."""
        # Log task start to WAL (Step 51)
        if self.worker_recovery:
            await self.worker_recovery.log_task_start(
                task_id=task_node.task_id,
                dag_id=graph.dag_id,
                node_id=task_node.task_id,
                input_data=task_node.kwargs,
            )

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
        await self._publish_event("dag.task_started", {
            "dag_id": graph.dag_id,
            "task_id": task_node.task_id,
            "func_name": task_node.func_name,
            "worker_id": worker_id,
        })

        try:
            should_use_huey = (
                self.use_huey or bool(task_node.kwargs.get("_use_huey", False))
            ) and self.huey_instance is not None

            async def _run_actual():
                if should_use_huey:
                    from src.backend.tasks.huey import execute_agent_node_task, async_wait_huey_result
                    clean_kwargs = {k: v for k, v in task_node.kwargs.items() if not k.startswith("_")}
                    huey_task = execute_agent_node_task(
                        func_name=task_node.func_name,
                        kwargs=clean_kwargs,
                        node_id=task_node.task_id,
                    )
                    timeout_val = task_node.timeout_seconds or 60.0
                    res = await async_wait_huey_result(huey_task, timeout=timeout_val)
                    if isinstance(res, dict) and res.get("status") == "error":
                        raise RuntimeError(res.get("error", "Huey task failed"))
                    return res
                else:
                    fn = self.task_registry.get(task_node.func_name)
                    if not fn:
                        raise KeyError(f"Function '{task_node.func_name}' not registered")
                    res = fn(**task_node.kwargs)
                    if inspect.iscoroutine(res):
                        res = await res
                    return res

            if task_node.timeout_seconds and task_node.timeout_seconds > 0:
                res = await asyncio.wait_for(_run_actual(), timeout=task_node.timeout_seconds)
            else:
                res = await _run_actual()

            graph.mark_completed(task_node.task_id, result=res)
            logger.info(f"Task '{task_node.task_id}' completed on {worker_id}")
            await self._publish_event("dag.task_completed", {
                "dag_id": graph.dag_id,
                "task_id": task_node.task_id,
                "worker_id": worker_id,
            })
            
            # Log task completion to WAL (Step 51)
            if self.worker_recovery:
                await self.worker_recovery.log_task_completion(
                    task_id=task_node.task_id,
                    output_data=res if isinstance(res, dict) else {"result": str(res)},
                )

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
        except (Exception, asyncio.TimeoutError) as exc:
            logger.warning(f"Task '{task_node.task_id}' failed: {exc}")
            # リトライ制御 (Step 42 & Step 52)
            task_node.retry_count += 1
            if task_node.retry_count <= task_node.retry_limit:
                logger.info(f"Retrying task '{task_node.task_id}' (attempt {task_node.retry_count}/{task_node.retry_limit})")
                task_node.status = "ready"
                # Metrics: record retry
                self.metrics.record_retry(task_node.task_id, task_node.retry_count)
            else:
                err_msg = f"Timeout after {task_node.timeout_seconds}s" if isinstance(exc, asyncio.TimeoutError) else str(exc)
                graph.mark_failed(task_node.task_id, err_msg)
                await self._publish_event("dag.task_failed", {
                    "dag_id": graph.dag_id,
                    "task_id": task_node.task_id,
                    "error": err_msg,
                })
                # Step 51: 下流タスクのカスケードキャンセル
                cancelled = graph.cascade_cancel_downstream(task_node.task_id, reason=f"Dependency {task_node.task_id} failed")
                if cancelled:
                    logger.info(f"Cascade cancelled downstream tasks of '{task_node.task_id}': {cancelled}")
                
                # Log task failure to WAL (Step 51)
                if self.worker_recovery:
                    await self.worker_recovery.log_task_completion(
                        task_id=task_node.task_id,
                        error=err_msg,
                    )
                
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
        """Release semaphores and update allocation tracking (Step 59)."""
        req = allocated_map.pop(task_id, None)
        if not req or self._semaphores is None:
            return
        # Release semaphores in reverse order of acquisition with error safeguard
        try:
            if req.gpu_mem_mb > 0:
                self._semaphores.gpu.release()
            ram_slots = max(1, int(req.ram_mb / 512))
            for _ in range(ram_slots):
                self._semaphores.ram.release()
            self._semaphores.cpu.release()
        except ValueError:
            pass  # Protection against semaphore released too many times

        # Keep active_allocations updated for monitoring
        self.active_allocations.cpu_cores = max(0.0, self.active_allocations.cpu_cores - req.cpu_cores)
        self.active_allocations.ram_mb = max(0, self.active_allocations.ram_mb - req.ram_mb)
        self.active_allocations.gpu_mem_mb = max(0, self.active_allocations.gpu_mem_mb - req.gpu_mem_mb)

    async def _acquire_resources(self, req: TaskResourceRequirement) -> None:
        """Acquire semaphores for required resources. Fixed order prevents deadlock."""
        self._init_semaphores()
        assert self._semaphores is not None
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
            self.active_async_tasks.pop(task_id, None)
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

    async def on_startup(self) -> list[str]:
        """Startup hook: scan for and resume all active DAGs (Step 54).
        
        If WorkerRecoveryManager is configured, delegates to it for zombie detection
        and recovery. Otherwise uses local checkpoint-based recovery.
        
        Returns list of DAG IDs that were resumed.
        """
        if self.worker_recovery:
            logger.info("Running WorkerRecoveryManager startup recovery...")
            recovered_tasks = await self.worker_recovery.recover_orphan_tasks()
            if recovered_tasks:
                logger.info(f"Recovered {len(recovered_tasks)} orphan tasks on startup")
            return recovered_tasks
        
        # Fallback: local checkpoint-based recovery
        logger.info("Running local checkpoint-based startup recovery...")
        checkpoints_dir = self.persistence.base_dir
        if not checkpoints_dir.exists():
            return []
        
        resumed_dags = set()
        for cp_file in checkpoints_dir.glob("*.json"):
            dag_id = cp_file.stem.split("_cp_")[0]
            if dag_id not in resumed_dags:
                try:
                    graph = self.auto_recover(dag_id)
                    if graph:
                        resumed_dags.add(dag_id)
                        logger.info(f"Auto-recovered DAG {dag_id} from checkpoint")
                except Exception as e:
                    logger.warning(f"Failed to auto-recover DAG {dag_id}: {e}")
        
        return list(resumed_dags)

    async def resume_from_checkpoint_with_wal(
        self,
        dag_id: str,
        graph: DAGGraph,
    ) -> DAGGraph:
        """Resume DAG from checkpoint using WAL for idempotent intermediate state (Step 55).
        
        Finds completed nodes from WAL and restores their outputs to graph nodes,
        allowing downstream nodes to execute without re-running completed work.
        
        Args:
            dag_id: The DAG identifier
            graph: The DAGGraph loaded from checkpoint
            
        Returns:
            Updated graph with completed node outputs restored from WAL
        """
        if not self.worker_recovery or not self.db_manager:
            logger.warning("WAL-based resume requires WorkerRecoveryManager and DatabaseManager")
            return graph

        completed_nodes = await self.worker_recovery.resume_dag_from_checkpoint(dag_id)
        logger.info(f"Resuming DAG {dag_id}: found {len(completed_nodes)} completed nodes in WAL")
        
        for node_id in completed_nodes:
            if node_id in graph.nodes:
                wal_entry = await self.worker_recovery.get_latest_wal_for_node(dag_id, node_id)
                if wal_entry and wal_entry.output_json:
                    try:
                        output_data = json.loads(wal_entry.output_json)
                        graph.nodes[node_id].result = output_data
                        graph.nodes[node_id].status = "completed"
                        graph.nodes[node_id].completed_at = wal_entry.created_at
                        logger.debug(f"Restored output for node {node_id} from WAL")
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse WAL output for node {node_id}")
        
        return graph

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