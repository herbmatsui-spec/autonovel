"""Pluggable Scheduling Policies (Step 3)."""
from __future__ import annotations

from typing import Protocol, List
from src.backend.tasks.dag_models import DAGTaskNode


class SchedulingPolicy(Protocol):
    """スケジューリングポリシーのプロトコル。"""
    def sort_ready_tasks(self, ready_tasks: List[DAGTaskNode]) -> List[DAGTaskNode]:
        """実行準備完了タスクを並び替える。"""
        ...
    
    def should_preempt(self, running_task: DAGTaskNode, new_task: DAGTaskNode) -> bool:
        """実行中タスクをプリエンプトして新タスクを優先するか。"""
        ...


class AffinityPriorityPolicy:
    """既存ロジック: アフィニティあり優先 → priority 降順。"""
    def __init__(self, worker_affinity_map: dict[str, str]):
        self.worker_affinity_map = worker_affinity_map
    
    def sort_ready_tasks(self, ready_tasks: List[DAGTaskNode]) -> List[DAGTaskNode]:
        def affinity_key(task: DAGTaskNode) -> int:
            chapter_key = f"{task.kwargs.get('book_id', 0)}:{task.kwargs.get('ep_num', 0)}"
            return 1 if chapter_key in self.worker_affinity_map else 0
        return sorted(ready_tasks, key=lambda t: (affinity_key(t), t.priority), reverse=True)
    
    def should_preempt(self, running_task: DAGTaskNode, new_task: DAGTaskNode) -> bool:
        return False  # プリエンプトなし


class FairRoundRobinPolicy:
    """同一優先度内でラウンドロビン。"""
    def __init__(self):
        self._counters: dict[str, int] = {}
    
    def sort_ready_tasks(self, ready_tasks: List[DAGTaskNode]) -> List[DAGTaskNode]:
        # priority 降順、同一 priority 内でラウンドロビン
        grouped: dict[int, List[DAGTaskNode]] = {}
        for t in ready_tasks:
            grouped.setdefault(t.priority, []).append(t)
        result = []
        for pri in sorted(grouped.keys(), reverse=True):
            lst = grouped[pri]
            idx = self._counters.get(f"pri_{pri}", 0) % len(lst)
            result.extend(lst[idx:] + lst[:idx])
            self._counters[f"pri_{pri}"] = (idx + 1) % len(lst)
        return result
    
    def should_preempt(self, running_task: DAGTaskNode, new_task: DAGTaskNode) -> bool:
        return False


class DeadlineAwarePolicy:
    """期限付きタスクを優先 (Earliest Deadline First)。"""
    def __init__(self, default_deadline_seconds: float = 300.0):
        self.default_deadline = default_deadline_seconds
    
    def _deadline_key(self, task: DAGTaskNode) -> float:
        from datetime import datetime, timedelta
        dl = task.kwargs.get("deadline_seconds", self.default_deadline)
        started = task.started_at or datetime.now()
        return (started + timedelta(seconds=dl)).timestamp()
    
    def sort_ready_tasks(self, ready_tasks: List[DAGTaskNode]) -> List[DAGTaskNode]:
        return sorted(ready_tasks, key=self._deadline_key)
    
    def should_preempt(self, running_task: DAGTaskNode, new_task: DAGTaskNode) -> bool:
        # 新タスクの期限が早ければプリエンプト
        return self._deadline_key(new_task) < self._deadline_key(running_task)


__all__ = [
    "SchedulingPolicy",
    "AffinityPriorityPolicy",
    "FairRoundRobinPolicy",
    "DeadlineAwarePolicy",
]