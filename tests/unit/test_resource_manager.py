"""Unit tests for ResourceManager GPU scheduling logic (Step 14)."""
import pytest
from src.backend.tasks.resource_manager import ResourceManager
from src.backend.tasks.dag_models import TaskResourceRequirement


def test_gpu_task_rejected_when_no_gpu_available():
    """GPU が 0MB の場合、gpu_mem_mb > 0 のタスクはスケジュール不可となることの検証."""
    rm = ResourceManager()
    task_req = TaskResourceRequirement(cpu_cores=1.0, ram_mb=512, gpu_mem_mb=2048)
    active_allocations = TaskResourceRequirement(cpu_cores=0.0, ram_mb=0, gpu_mem_mb=0)

    assert rm.can_schedule(task_req, active_allocations) is False


def test_gpu_task_accepted_when_gpu_available():
    """GPU が十分な場合、gpu_mem_mb > 0 のタスクはスケジュール可能となることの検証."""
    rm = ResourceManager()
    task_req = TaskResourceRequirement(cpu_cores=1.0, ram_mb=512, gpu_mem_mb=2048)
    active_allocations = TaskResourceRequirement(cpu_cores=0.0, ram_mb=0, gpu_mem_mb=0)
    rm._available = TaskResourceRequirement(cpu_cores=4.0, ram_mb=4096, gpu_mem_mb=8192)

    assert rm.can_schedule(task_req, active_allocations) is True


def test_gpu_task_rejected_when_overallocated():
    """GPU 要求量が利用可能な量を超える場合、スケジュール不可となることの検証."""
    rm = ResourceManager()
    task_req = TaskResourceRequirement(cpu_cores=1.0, ram_mb=512, gpu_mem_mb=4096)
    active_allocations = TaskResourceRequirement(cpu_cores=0.0, ram_mb=0, gpu_mem_mb=4096)
    rm._available = TaskResourceRequirement(cpu_cores=4.0, ram_mb=4096, gpu_mem_mb=4096)

    assert rm.can_schedule(task_req, active_allocations) is False


def test_non_gpu_task_accepted_when_no_gpu():
    """GPU 不要タスクは GPU が 0MB でもスケジュール可能となることの検証."""
    rm = ResourceManager()
    task_req = TaskResourceRequirement(cpu_cores=1.0, ram_mb=512, gpu_mem_mb=0)
    active_allocations = TaskResourceRequirement(cpu_cores=0.0, ram_mb=0, gpu_mem_mb=0)

    assert rm.can_schedule(task_req, active_allocations) is True
