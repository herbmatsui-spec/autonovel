"""Tests for Worker Recovery Manager (Steps 51-53, 56-57)."""
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from src.backend.database.core import DatabaseManager
from src.backend.database.models import TaskWALLogModel
from src.backend.tasks.worker_recovery import WorkerRecoveryManager, RecoveryConfig


@pytest.fixture
def mock_db_manager():
    """Create a mock database manager with async session."""
    db_manager = MagicMock(spec=DatabaseManager)
    session = AsyncMock()
    db_manager.get_session.return_value.__aenter__.return_value = session
    db_manager.get_session.return_value.__aexit__.return_value = None
    return db_manager, session


@pytest.fixture
def recovery_config():
    """Create a test recovery config."""
    return RecoveryConfig(
        heartbeat_interval_seconds=30,
        zombie_threshold_seconds=300,
        max_recovery_attempts=3,
        alert_on_recovery=True,
    )


@pytest.fixture
def recovery_manager(mock_db_manager, recovery_config):
    """Create a WorkerRecoveryManager instance with mocked DB."""
    db_manager, _ = mock_db_manager
    return WorkerRecoveryManager(db_manager=db_manager, config=recovery_config)


class TestWorkerRecoveryManager:
    """Tests for WorkerRecoveryManager."""

    @pytest.mark.asyncio
    async def test_start_stop(self, recovery_manager):
        """Test starting and stopping the recovery manager."""
        await recovery_manager.start()
        assert recovery_manager._running is True
        assert recovery_manager._heartbeat_task is not None
        assert recovery_manager._recovery_task is not None
        
        await recovery_manager.stop()
        assert recovery_manager._running is False

    @pytest.mark.asyncio
    async def test_log_task_start(self, recovery_manager, mock_db_manager):
        """Test logging task start to WAL (Step 51)."""
        _, session = mock_db_manager
        
        await recovery_manager.log_task_start(
            task_id="task_1",
            dag_id="dag_1",
            node_id="node_1",
            input_data={"book_id": 1, "ep_num": 1},
        )
        
        session.add.assert_called_once()
        session.commit.assert_called_once()
        
        # Verify the added log entry
        added_log = session.add.call_args[0][0]
        assert isinstance(added_log, TaskWALLogModel)
        assert added_log.task_id == "task_1"
        assert added_log.dag_id == "dag_1"
        assert added_log.node_id == "node_1"
        assert added_log.state == "running"
        assert added_log.input_json is not None

    @pytest.mark.asyncio
    async def test_log_task_completion_success(self, recovery_manager, mock_db_manager):
        """Test logging successful task completion to WAL (Step 51)."""
        _, session = mock_db_manager
        
        await recovery_manager.log_task_completion(
            task_id="task_1",
            output_data={"result": "success"},
        )
        
        session.execute.assert_called_once()
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_task_completion_failure(self, recovery_manager, mock_db_manager):
        """Test logging failed task completion to WAL (Step 51)."""
        _, session = mock_db_manager
        
        await recovery_manager.log_task_completion(
            task_id="task_1",
            error="Task timed out",
        )
        
        session.execute.assert_called_once()
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_running_task_heartbeats(self, recovery_manager, mock_db_manager):
        """Test updating heartbeats for running tasks (Step 51)."""
        _, session = mock_db_manager
        
        # Mock running tasks
        mock_logs = [
            MagicMock(spec=TaskWALLogModel, task_id=f"task_{i}", state="running")
            for i in range(3)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        session.execute.return_value = mock_result
        
        await recovery_manager.update_running_task_heartbeats()
        
        session.execute.assert_called_once()
        session.commit.assert_called_once()
        
        # Verify heartbeats were updated
        for log in mock_logs:
            assert log.heartbeat_at is not None

    @pytest.mark.asyncio
    async def test_detect_zombie_tasks(self, recovery_manager, mock_db_manager):
        """Test detecting zombie tasks (Step 52)."""
        _, session = mock_db_manager
        
        # Mock zombie tasks (heartbeat older than threshold)
        old_time = datetime.now() - timedelta(seconds=400)
        mock_zombies = [
            MagicMock(spec=TaskWALLogModel, task_id=f"zombie_{i}", heartbeat_at=old_time)
            for i in range(2)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_zombies
        session.execute.return_value = mock_result
        
        zombies = await recovery_manager.detect_zombie_tasks()
        
        assert len(zombies) == 2
        assert zombies[0].task_id == "zombie_0"
        assert zombies[1].task_id == "zombie_1"

    @pytest.mark.asyncio
    async def test_detect_zombie_tasks_empty(self, recovery_manager, mock_db_manager):
        """Test detecting zombie tasks when none exist."""
        _, session = mock_db_manager
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result
        
        zombies = await recovery_manager.detect_zombie_tasks()
        
        assert len(zombies) == 0

    @pytest.mark.asyncio
    async def test_recover_orphan_tasks(self, recovery_manager, mock_db_manager):
        """Test recovering orphan/zombie tasks (Step 53)."""
        _, session = mock_db_manager
        
        # Mock zombie tasks
        old_time = datetime.now() - timedelta(seconds=400)
        mock_zombies = [
            MagicMock(spec=TaskWALLogModel, task_id=f"zombie_{i}", dag_id="dag_1", node_id=f"node_{i}", heartbeat_at=old_time)
            for i in range(2)
        ]
        
        # Mock detect_zombie_tasks to return zombies
        with patch.object(recovery_manager, 'detect_zombie_tasks', return_value=mock_zombies):
            # Mock _get_recovery_attempt_count to return 0 (first attempt)
            with patch.object(recovery_manager, '_get_recovery_attempt_count', return_value=0):
                recovered = await recovery_manager.recover_orphan_tasks()
        
        assert len(recovered) == 2
        assert recovered == ["zombie_0", "zombie_1"]
        session.commit.assert_called_once()
        
        # Verify zombies were marked as pending
        for zombie in mock_zombies:
            assert zombie.state == "pending"
            assert zombie.heartbeat_at is not None

    @pytest.mark.asyncio
    async def test_recover_orphan_tasks_poison_pill(self, recovery_manager, mock_db_manager):
        """Test poison pill prevention - max recovery attempts exceeded (Step 56)."""
        _, session = mock_db_manager
        
        # Mock zombie tasks
        old_time = datetime.now() - timedelta(seconds=400)
        mock_zombie = MagicMock(
            spec=TaskWALLogModel,
            task_id="zombie_1",
            dag_id="dag_1",
            node_id="node_1",
            heartbeat_at=old_time,
        )
        
        with patch.object(recovery_manager, 'detect_zombie_tasks', return_value=[mock_zombie]):
            # Mock _get_recovery_attempt_count to return 3 (exceeded max of 3)
            with patch.object(recovery_manager, '_get_recovery_attempt_count', return_value=3):
                recovered = await recovery_manager.recover_orphan_tasks()
        
        assert len(recovered) == 0
        # Verify task was marked as failed
        session.execute.assert_called()
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_get_latest_wal_for_node(self, recovery_manager, mock_db_manager):
        """Test getting latest WAL entry for a node."""
        _, session = mock_db_manager
        
        mock_wal = MagicMock(spec=TaskWALLogModel, task_id="task_1", node_id="node_1", output_json='{"result": "data"}')
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_wal
        session.execute.return_value = mock_result
        
        wal = await recovery_manager.get_latest_wal_for_node("dag_1", "node_1")
        
        assert wal is not None
        assert wal.task_id == "task_1"

    @pytest.mark.asyncio
    async def test_resume_dag_from_checkpoint(self, recovery_manager, mock_db_manager):
        """Test resuming DAG from WAL checkpoint (Step 55)."""
        _, session = mock_db_manager
        
        # Mock completed WAL entries
        mock_logs = [
            MagicMock(spec=TaskWALLogModel, node_id="node_1", output_json='{"result": "output1"}'),
            MagicMock(spec=TaskWALLogModel, node_id="node_2", output_json='{"result": "output2"}'),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        session.execute.return_value = mock_result
        
        completed_nodes = await recovery_manager.resume_dag_from_checkpoint("dag_1")
        
        assert len(completed_nodes) == 2
        assert "node_1" in completed_nodes
        assert "node_2" in completed_nodes

    @pytest.mark.asyncio
    async def test_pause_downstream_tasks(self, recovery_manager, mock_db_manager):
        """Test pausing downstream tasks of a failed node."""
        _, session = mock_db_manager
        
        mock_tasks = [
            MagicMock(spec=TaskWALLogModel, task_id=f"task_{i}", state="running")
            for i in range(3)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_tasks
        session.execute.return_value = mock_result
        
        paused = await recovery_manager.pause_downstream_tasks("dag_1", "failed_node")
        
        assert len(paused) == 3
        session.commit.assert_called_once()
        
        # Verify tasks were marked as pending
        for task in mock_tasks:
            assert task.state == "pending"


class TestRecoveryConfig:
    """Tests for RecoveryConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RecoveryConfig()
        assert config.heartbeat_interval_seconds == 30
        assert config.zombie_threshold_seconds == 300
        assert config.max_recovery_attempts == 3
        assert config.alert_on_recovery is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = RecoveryConfig(
            heartbeat_interval_seconds=10,
            zombie_threshold_seconds=60,
            max_recovery_attempts=5,
            alert_on_recovery=False,
        )
        assert config.heartbeat_interval_seconds == 10
        assert config.zombie_threshold_seconds == 60
        assert config.max_recovery_attempts == 5
        assert config.alert_on_recovery is False


class TestWorkerRecoveryManagerIntegration:
    """Integration-style tests for WorkerRecoveryManager."""

    @pytest.mark.asyncio
    async def test_full_recovery_cycle(self, recovery_manager, mock_db_manager):
        """Test a full recovery cycle: log start, detect zombie, recover."""
        _, session = mock_db_manager
        
        # Log task start
        await recovery_manager.log_task_start(
            task_id="task_1",
            dag_id="dag_1",
            node_id="node_1",
            input_data={"param": "value"},
        )
        
        # Simulate time passing and task becoming zombie
        old_time = datetime.now() - timedelta(seconds=400)
        mock_zombie = MagicMock(
            spec=TaskWALLogModel,
            task_id="task_1",
            dag_id="dag_1",
            node_id="node_1",
            heartbeat_at=old_time,
            state="running",
        )
        
        # Mock detect_zombie_tasks
        with patch.object(recovery_manager, 'detect_zombie_tasks', return_value=[mock_zombie]):
            with patch.object(recovery_manager, '_get_recovery_attempt_count', return_value=0):
                recovered = await recovery_manager.recover_orphan_tasks()
        
        assert "task_1" in recovered
        assert mock_zombie.state == "pending"

    @pytest.mark.asyncio
    async def test_heartbeat_loop_updates_multiple_tasks(self, recovery_manager, mock_db_manager):
        """Test heartbeat loop updates multiple running tasks."""
        _, session = mock_db_manager
        
        mock_logs = [
            MagicMock(spec=TaskWALLogModel, task_id=f"task_{i}", state="running", heartbeat_at=None)
            for i in range(5)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_logs
        session.execute.return_value = mock_result
        
        await recovery_manager.update_running_task_heartbeats()
        
        # All 5 tasks should have updated heartbeats
        for log in mock_logs:
            assert log.heartbeat_at is not None
        
        session.commit.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])