# tests/unit/test_orchestrator_skills.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from src.agents.orchestrator import Orchestrator, AgentName
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult


class MockSkillA(SkillAgent):
    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(next_agent=None, artifacts={})


class MockSkillB(SkillAgent):
    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(next_agent=None, artifacts={})


class MockSkillC(SkillAgent):
    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(next_agent=None, artifacts={})


def test_register_discovered_skills():
    orch = Orchestrator(nodes={})
    orch.register_discovered_skills('src.agents.skills')
    assert 'planning' in orch._skill_registry
    assert 'bible' in orch._skill_registry


def test_build_execution_order():
    orch = Orchestrator(nodes={})
    manifest = [
        {'name': 'A', 'depends_on': [], 'runs_after': [], 'runs_before': ['B']},
        {'name': 'B', 'depends_on': ['A'], 'runs_after': ['A'], 'runs_before': ['C']},
        {'name': 'C', 'depends_on': ['B'], 'runs_after': ['B'], 'runs_before': []},
    ]
    available = {'A': MockSkillA, 'B': MockSkillB, 'C': MockSkillC}
    order = orch.build_execution_order(manifest, available)
    assert [cls.__name__ for cls in order] == ['MockSkillA', 'MockSkillB', 'MockSkillC']


def test_build_execution_order_circular():
    orch = Orchestrator(nodes={})
    manifest = [
        {'name': 'A', 'depends_on': ['B'], 'runs_after': [], 'runs_before': []},
        {'name': 'B', 'depends_on': ['A'], 'runs_after': [], 'runs_before': []},
    ]
    available = {'A': MockSkillA, 'B': MockSkillB}
    with pytest.raises(RuntimeError):
        orch.build_execution_order(manifest, available)


def test_replace_skill():
    orch = Orchestrator(nodes={})
    orch.register_discovered_skills('src.agents.skills')
    original = orch.get_skill_class('planning')
    class NewPlanning(SkillAgent):
        async def execute(self, ctx): pass
    orch.replace_skill('planning', NewPlanning)
    assert orch.get_skill_class('planning') is NewPlanning
    # 元に戻す
    orch.replace_skill('planning', original)