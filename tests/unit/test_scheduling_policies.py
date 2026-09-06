"""Tests for Scheduling Policies (Step 3)."""
import pytest
from src.backend.tasks.scheduling_policies import (
    AffinityPriorityPolicy,
    FairRoundRobinPolicy,
    DeadlineAwarePolicy,
)
from src.backend.tasks.dag_models import DAGTaskNode


def test_affinity_policy_prefers_same_chapter():
    """アフィニティありのタスクが優先されること。"""
    policy = AffinityPriorityPolicy({"1:1": "worker_1"})
    t1 = DAGTaskNode(task_id="t1", func_name="f", kwargs={"book_id": 1, "ep_num": 1}, priority=0)
    t2 = DAGTaskNode(task_id="t2", func_name="f", kwargs={"book_id": 2, "ep_num": 1}, priority=10)
    sorted_tasks = policy.sort_ready_tasks([t2, t1])
    assert sorted_tasks[0].task_id == "t1"  # アフィニティあり優先


def test_affinity_policy_respects_priority_when_no_affinity():
    """アフィニティなしなら priority 降順。"""
    policy = AffinityPriorityPolicy({})
    t1 = DAGTaskNode(task_id="t1", func_name="f", kwargs={"book_id": 1, "ep_num": 1}, priority=5)
    t2 = DAGTaskNode(task_id="t2", func_name="f", kwargs={"book_id": 2, "ep_num": 1}, priority=10)
    sorted_tasks = policy.sort_ready_tasks([t1, t2])
    assert sorted_tasks[0].task_id == "t2"  # priority 高い方優先


def test_fair_round_robin_rotates():
    """同一 priority 内でラウンドロビンでローテーション。"""
    policy = FairRoundRobinPolicy()
    tasks = [DAGTaskNode(task_id=f"t{i}", func_name="f", priority=5) for i in range(3)]
    order1 = [t.task_id for t in policy.sort_ready_tasks(tasks)]
    order2 = [t.task_id for t in policy.sort_ready_tasks(tasks)]
    order3 = [t.task_id for t in policy.sort_ready_tasks(tasks)]
    order4 = [t.task_id for t in policy.sort_ready_tasks(tasks)]
    # 4回で元に戻る（カウンタは 0,1,2,0...）
    assert order1 != order2
    assert order2 != order3
    assert order3 != order4
    assert order4 == order1


def test_fair_round_robin_priority_order():
    """priority 降順は維持される。"""
    policy = FairRoundRobinPolicy()
    t_low = DAGTaskNode(task_id="t_low", func_name="f", priority=1)
    t_high = DAGTaskNode(task_id="t_high", func_name="f", priority=10)
    sorted_tasks = policy.sort_ready_tasks([t_low, t_high])
    assert sorted_tasks[0].task_id == "t_high"


def test_deadline_aware_policy_earliest_deadline_first():
    """期限が早いタスクが優先される (EDF)。"""
    policy = DeadlineAwarePolicy(default_deadline_seconds=300.0)
    t1 = DAGTaskNode(task_id="t1", func_name="f", kwargs={"deadline_seconds": 100})
    t2 = DAGTaskNode(task_id="t2", func_name="f", kwargs={"deadline_seconds": 50})
    t3 = DAGTaskNode(task_id="t3", func_name="f", kwargs={"deadline_seconds": 200})
    sorted_tasks = policy.sort_ready_tasks([t1, t2, t3])
    assert sorted_tasks[0].task_id == "t2"  # 最も期限が早い
    assert sorted_tasks[1].task_id == "t1"
    assert sorted_tasks[2].task_id == "t3"


def test_deadline_aware_policy_preempt():
    """新タスクの期限が早ければプリエンプトする。"""
    policy = DeadlineAwarePolicy(default_deadline_seconds=300.0)
    running = DAGTaskNode(task_id="running", func_name="f", kwargs={"deadline_seconds": 200})
    new_early = DAGTaskNode(task_id="new_early", func_name="f", kwargs={"deadline_seconds": 50})
    new_late = DAGTaskNode(task_id="new_late", func_name="f", kwargs={"deadline_seconds": 500})
    assert policy.should_preempt(running, new_early) is True
    assert policy.should_preempt(running, new_late) is False


def test_scheduler_can_switch_policies():
    """DAGScheduler でポリシー動的切替可能。"""
    from src.backend.tasks.dag_scheduler import DAGScheduler
    from src.backend.tasks.scheduling_policies import FairRoundRobinPolicy
    
    scheduler = DAGScheduler()
    # デフォルトは AffinityPriorityPolicy
    assert type(scheduler.scheduling_policy).__name__ == "AffinityPriorityPolicy"
    
    # 切替
    scheduler.set_scheduling_policy(FairRoundRobinPolicy())
    assert type(scheduler.scheduling_policy).__name__ == "FairRoundRobinPolicy"