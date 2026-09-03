# tests/unit/test_skill_metrics.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import Orchestrator, AgentContext, AgentResult


class MetricSkill(SkillAgent):
    async def execute(self, ctx: AgentContext) -> AgentResult:
        return AgentResult(next_agent=None, artifacts={})


class FailingSkill(SkillAgent):
    async def execute(self, ctx: AgentContext) -> AgentResult:
        raise ValueError("Intentional failure")


@pytest.fixture(autouse=True)
def reset_metrics():
    SkillAgent.reset_metrics()
    yield
    SkillAgent.reset_metrics()


@pytest.mark.asyncio
async def test_skill_metrics_success(reset_metrics):
    """成功時のメトリクス記録"""
    skill = MetricSkill()
    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
    await skill.run(ctx)

    metrics = SkillAgent.get_metrics()
    assert "MetricSkill" in metrics
    assert metrics["MetricSkill"]["success_count"] == 1
    assert metrics["MetricSkill"]["error_count"] == 0
    assert metrics["MetricSkill"]["total_executions"] == 1
    assert metrics["MetricSkill"]["avg_duration_sec"] >= 0


@pytest.mark.asyncio
async def test_skill_metrics_error(reset_metrics):
    """エラー時のメトリクス記録"""
    skill = FailingSkill()
    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
    with pytest.raises(ValueError):
        await skill.run(ctx)

    metrics = SkillAgent.get_metrics()
    assert "FailingSkill" in metrics
    assert metrics["FailingSkill"]["success_count"] == 0
    assert metrics["FailingSkill"]["error_count"] == 1


@pytest.mark.asyncio
async def test_orchestrator_get_skill_metrics(reset_metrics):
    """オーケストレーター経由でメトリクス取得"""
    orch = Orchestrator(nodes={})
    skill = MetricSkill()
    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
    await skill.run(ctx)

    metrics = orch.get_skill_metrics()
    assert "MetricSkill" in metrics