"""Worker Recovery Manager for DAG Task Crash Recovery (Steps 51-53, 56-57)."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select, update

from src.backend.database.core import DatabaseManager
from src.backend.database.models import TaskWALLogModel

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RecoveryConfig:
    """Configuration for worker recovery behavior."""
    heartbeat_interval_seconds: int = 30
    zombie_threshold_seconds: int = 300
    max_recovery_attempts: int = 3
    alert_on_recovery: bool = True


class WorkerRecoveryManager:
    """Manages worker crash detection and automatic task recovery using WAL."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        config: RecoveryConfig | None = None,
        event_bus: Any = None,
    ) -> None:
        self.db_manager = db_manager
        self.config = config or RecoveryConfig()
        self.event_bus = event_bus
        self._running = False
        self._heartbeat_task: asyncio.Task | None = None
        self._recovery_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the heartbeat and recovery background tasks."""
        if self._running:
            return
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._recovery_task = asyncio.create_task(self._recovery_loop())
        logger.info("WorkerRecoveryManager started")

    async def stop(self) -> None:
        """Stop the background tasks."""
        self._running = False
        for task in (self._heartbeat_task, self._recovery_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("WorkerRecoveryManager stopped")

    async def _heartbeat_loop(self) -> None:
        """Periodically update heartbeats for running tasks."""
        while self._running:
            try:
                await self.update_running_task_heartbeats()
            except Exception as e:
                logger.error(f"Heartbeat update failed: {e}")
            await asyncio.sleep(self.config.heartbeat_interval_seconds)

    async def _recovery_loop(self) -> None:
        """Periodically scan for and recover zombie tasks."""
        while self._running:
            try:
                await self.recover_orphan_tasks()
            except Exception as e:
                logger.error(f"Orphan task recovery failed: {e}")
            await asyncio.sleep(self.config.zombie_threshold_seconds)

    async def update_running_task_heartbeats(self) -> None:
        """Update heartbeat_at for all tasks in 'running' state (Step 51)."""
        async with self.db_manager.get_session() as session:
            stmt = select(TaskWALLogModel).where(TaskWALLogModel.state == "running")
            result = await session.execute(stmt)
            running_logs = result.scalars().all()

            if not running_logs:
                return

            now = datetime.now()
            for log in running_logs:
                log.heartbeat_at = now

            await session.commit()
            logger.debug(f"Updated heartbeats for {len(running_logs)} running tasks")

    async def detect_zombie_tasks(self) -> list[TaskWALLogModel]:
        """Detect orphan/zombie tasks (Step 52).
        
        A task is considered a zombie if:
        - state == 'running'
        - heartbeat_at is older than zombie_threshold_seconds (default 5 minutes)
        """
        threshold = datetime.now() - timedelta(seconds=self.config.zombie_threshold_seconds)
        
        async with self.db_manager.get_session() as session:
            stmt = select(TaskWALLogModel).where(
                TaskWALLogModel.state == "running",
                TaskWALLogModel.heartbeat_at < threshold,
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def recover_orphan_tasks(self) -> list[str]:
        """Recover zombie tasks by resetting them to 'pending' for re-scheduling (Step 53, 56).
        
        Returns list of recovered task_ids.
        """
        zombies = await self.detect_zombie_tasks()
        if not zombies:
            return []

        recovered_ids = []
        async with self.db_manager.get_session() as session:
            for zombie in zombies:
                recovery_attempts = await self._get_recovery_attempt_count(session, zombie.task_id)
                
                if recovery_attempts >= self.config.max_recovery_attempts:
                    logger.warning(
                        f"Task {zombie.task_id} (node {zombie.node_id}) exceeded max recovery "
                        f"attempts ({self.config.max_recovery_attempts}). Marking as failed."
                    )
                    await self._mark_task_failed(
                        session, 
                        zombie.task_id, 
                        f"Exceeded max recovery attempts ({self.config.max_recovery_attempts})"
                    )
                    await self._emit_alert(
                        "poison_pill",
                        task_id=zombie.task_id,
                        dag_id=zombie.dag_id,
                        node_id=zombie.node_id,
                        attempts=recovery_attempts,
                    )
                    continue

                zombie.state = "pending"
                zombie.heartbeat_at = datetime.now()
                recovered_ids.append(zombie.task_id)
                logger.info(
                    f"Recovered zombie task {zombie.task_id} (dag: {zombie.dag_id}, "
                    f"node: {zombie.node_id}, attempt: {recovery_attempts + 1})"
                )

            await session.commit()

        if recovered_ids and self.config.alert_on_recovery:
            for task_id in recovered_ids:
                zombie = next(z for z in zombies if z.task_id == task_id)
                await self._emit_alert(
                    "auto_recovery",
                    task_id=task_id,
                    dag_id=zombie.dag_id,
                    node_id=zombie.node_id,
                )

        return recovered_ids

    async def _get_recovery_attempt_count(self, session, task_id: str) -> int:
        """Count previous recovery attempts for a task."""
        stmt = select(TaskWALLogModel).where(
            TaskWALLogModel.task_id == task_id,
            TaskWALLogModel.state.in_(["pending", "running"]),
        )
        result = await session.execute(stmt)
        return len(list(result.scalars().all())) - 1

    async def _mark_task_failed(self, session, task_id: str, error: str) -> None:
        """Mark a task as failed in WAL."""
        stmt = update(TaskWALLogModel).where(TaskWALLogModel.task_id == task_id).values(
            state="failed",
            output_json=json.dumps({"error": error}),
        )
        await session.execute(stmt)

    async def _emit_alert(self, alert_type: str, **kwargs) -> None:
        """Emit recovery alert to event bus and logs (Step 57)."""
        alert_data = {
            "alert_type": alert_type,
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        }
        logger.warning(f"RECOVERY ALERT: {alert_data}")
        
        if self.event_bus:
            try:
                if hasattr(self.event_bus, "publish_async"):
                    await self.event_bus.publish_async("worker.recovery_alert", alert_data)
                elif hasattr(self.event_bus, "publish"):
                    result = self.event_bus.publish("worker.recovery_alert", alert_data)
                    if asyncio.iscoroutine(result):
                        await result
            except Exception as e:
                logger.debug(f"Failed to publish recovery alert: {e}")

    async def log_task_start(
        self,
        task_id: str,
        dag_id: str,
        node_id: str,
        input_data: dict[str, Any] | None = None,
    ) -> None:
        """Log task execution start to WAL."""
        async with self.db_manager.get_session() as session:
            log = TaskWALLogModel(
                task_id=task_id,
                dag_id=dag_id,
                node_id=node_id,
                state="running",
                input_json=json.dumps(input_data) if input_data else None,
                heartbeat_at=datetime.now(),
            )
            session.add(log)
            await session.commit()

    async def log_task_completion(
        self,
        task_id: str,
        output_data: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Log task completion (success or failure) to WAL."""
        state = "failed" if error else "completed"
        async with self.db_manager.get_session() as session:
            stmt = (
                update(TaskWALLogModel)
                .where(TaskWALLogModel.task_id == task_id)
                .values(
                    state=state,
                    output_json=json.dumps(output_data or {"error": error}),
                    heartbeat_at=datetime.now(),
                )
            )
            await session.execute(stmt)
            await session.commit()

    async def get_latest_wal_for_node(self, dag_id: str, node_id: str) -> Optional[TaskWALLogModel]:
        """Get the latest WAL entry for a specific node (for checkpoint resume)."""
        async with self.db_manager.get_session() as session:
            stmt = (
                select(TaskWALLogModel)
                .where(
                    TaskWALLogModel.dag_id == dag_id,
                    TaskWALLogModel.node_id == node_id,
                )
                .order_by(TaskWALLogModel.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def resume_dag_from_checkpoint(self, dag_id: str) -> list[str]:
        """Resume a DAG from its latest WAL checkpoint.
        
        Finds all completed nodes and returns their outputs for downstream consumption.
        Returns list of node_ids that can be resumed from.
        """
        async with self.db_manager.get_session() as session:
            stmt = select(TaskWALLogModel).where(
                TaskWALLogModel.dag_id == dag_id,
                TaskWALLogModel.state == "completed",
            ).order_by(TaskWALLogModel.created_at)
            result = await session.execute(stmt)
            completed_logs = result.scalars().all()

            node_outputs = {}
            for log in completed_logs:
                if log.output_json:
                    try:
                        node_outputs[log.node_id] = json.loads(log.output_json)
                    except json.JSONDecodeError:
                        pass

            logger.info(f"Resuming DAG {dag_id} from checkpoint with {len(node_outputs)} completed nodes")
            return list(node_outputs.keys())

    async def get_pending_tasks_for_dag(self, dag_id: str) -> list[TaskWALLogModel]:
        """Get all pending tasks for a DAG that need to be executed."""
        async with self.db_manager.get_session() as session:
            stmt = select(TaskWALLogModel).where(
                TaskWALLogModel.dag_id == dag_id,
                TaskWALLogModel.state == "pending",
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def pause_downstream_tasks(self, dag_id: str, failed_node_id: str) -> list[str]:
        """Pause all downstream tasks of a failed node by setting them to 'pending'."""
        async with self.db_manager.get_session() as session:
            stmt = select(TaskWALLogModel).where(
                TaskWALLogModel.dag_id == dag_id,
                TaskWALLogModel.state.in_(["pending", "ready", "running"]),
            )
            result = await session.execute(stmt)
            tasks = result.scalars().all()

            paused = []
            for task in tasks:
                task.state = "pending"
                paused.append(task.task_id)

            await session.commit()
            return paused


async def create_worker_recovery_manager(
    db_manager: DatabaseManager,
    event_bus: Any = None,
    **config_kwargs,
) -> WorkerRecoveryManager:
    """Factory function to create and configure WorkerRecoveryManager."""
    config = RecoveryConfig(**config_kwargs)
    manager = WorkerRecoveryManager(db_manager, config, event_bus)
    return manager


__all__ = [
    "WorkerRecoveryManager",
    "RecoveryConfig",
    "create_worker_recovery_manager",
]