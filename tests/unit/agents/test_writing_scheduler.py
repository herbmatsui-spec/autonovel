import pytest
from src.agents.writing_scheduler import WritingScheduler

def test_writing_scheduler_dependency_graph():
    scheduler = WritingScheduler()
    scheduler.add_task(episode=1, depends_on=[])
    scheduler.add_task(episode=2, depends_on=[1])
    
    order = scheduler.get_execution_order()
    assert order == [1, 2]
