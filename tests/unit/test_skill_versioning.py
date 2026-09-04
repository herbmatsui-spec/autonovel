# tests/unit/test_skill_versioning.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.orchestrator import Orchestrator
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult


class MockSkillV1(SkillAgent):
    version = "1.0"
    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(next_agent=None, artifacts={"version": "v1"})


class MockSkillV2(SkillAgent):
    version = "2.0"
    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(next_agent=None, artifacts={"version": "v2"})


@pytest.fixture(autouse=True)
def reset_metrics():
    SkillAgent.reset_metrics()
    yield
    SkillAgent.reset_metrics()


def test_orchestrator_default_version():
    """デフォルトバージョンが v1"""
    orch = Orchestrator(nodes={})
    assert orch.get_active_version() == "v1"


def test_orchestrator_register_v1():
    """v1 スキル登録"""
    orch = Orchestrator(nodes={})
    orch.register_discovered_skills('src.agents.skills.v1')
    assert orch.get_active_version() == "v1"
    assert 'planning' in orch._skill_registry


def test_orchestrator_switch_version():
    """バージョン切替"""
    orch = Orchestrator(nodes={})
    orch.register_discovered_skills('src.agents.skills.v1')
    assert orch.get_active_version() == "v1"
    
    # v2 へ切替（v2 は空でもエラーにならない）
    orch.set_skill_version('v2')
    assert orch.get_active_version() == "v2"


def test_orchestrator_invalid_version():
    """無効なバージョンでエラー"""
    orch = Orchestrator(nodes={})
    with pytest.raises(ValueError):
        orch.set_skill_version('v3')


@pytest.mark.asyncio
async def test_skill_version_attribute():
    """スキルの version 属性確認"""
    assert MockSkillV1.version == "1.0"
    assert MockSkillV2.version == "2.0"
    
    skill1 = MockSkillV1()
    skill2 = MockSkillV2()
    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
    
    result1 = await skill1.execute(ctx)
    result2 = await skill2.execute(ctx)
    
    assert result1.artifacts["version"] == "v1"
    assert result2.artifacts["version"] == "v2"