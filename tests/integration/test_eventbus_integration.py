# tests/integration/test_eventbus_integration.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.event_bus import EventBus, AgentEvent
from src.agents.orchestrator import Orchestrator, AgentContext, AgentResult, AgentName
from src.agents.skill_base import SkillAgent


class EventEmittingSkill(SkillAgent):
    def __init__(self, *args, should_fail: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.should_fail = should_fail

    async def execute(self, ctx: AgentContext) -> AgentResult:
        await self.emit_event_sync("skill.started", {"book_id": ctx.book_id, "ep_num": ctx.ep_num})
        if self.should_fail:
            await self.emit_event_sync("skill.error", {"book_id": ctx.book_id, "ep_num": ctx.ep_num, "error": "Intentional failure"})
            raise ValueError("Intentional failure")
        await self.emit_event_sync("skill.completed", {"book_id": ctx.book_id, "ep_num": ctx.ep_num, "result": "success"})
        return AgentResult(next_agent=None, artifacts={"skill_executed": True})


@pytest.mark.asyncio
async def test_eventbus_publish_subscribe():
    """EventBus の publish/subscribe 動作確認"""
    bus = EventBus()
    received = []

    async def handler(event: AgentEvent):
        received.append(event)

    bus.subscribe("test_agent", handler)

    event = AgentEvent(
        agent="test_agent",
        payload={"key": "value"},
        correlation_id="test-123",
    )
    await bus.publish_sync(event)

    assert len(received) == 1
    assert received[0].agent == "test_agent"
    assert received[0].payload == {"key": "value"}
    assert received[0].correlation_id == "test-123"


@pytest.mark.asyncio
async def test_skill_emit_event():
    """SkillAgent.emit_event でイベント発行されること"""
    bus = EventBus()
    received = []

    async def handler(event: AgentEvent):
        received.append(event)

    bus.subscribe("EventEmittingSkill", handler)

    skill = EventEmittingSkill(event_bus=bus)
    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
    
    result = await skill.execute(ctx)

    # publish_sync は SkillAgent.emit_event 内で使われないため、
    # 手動で flush するか、publish の戻り値を待つ必要がある
    # ここでは簡易的に sleep で待つ
    import asyncio
    await asyncio.sleep(0.1)

    assert result.artifacts.get("skill_executed") is True
    assert len(received) >= 1
    
    # started イベント
    started_events = [e for e in received if e.payload.get("event") == "skill.started"]
    assert len(started_events) >= 1


@pytest.mark.asyncio
async def test_orchestrator_emits_events():
    """Orchestrator.run でイベントが発行されること"""
    bus = EventBus()
    received = []

    async def handler(event: AgentEvent):
        received.append(event)

    bus.subscribe("test_agent", handler)
    bus.subscribe("test_agent2", handler)

    skill1 = EventEmittingSkill(event_bus=bus)
    skill2 = EventEmittingSkill(event_bus=bus)

    async def node1(ctx): return await skill1.execute(ctx)
    async def node2(ctx): return await skill2.execute(ctx)

    orch = Orchestrator(
        nodes={
            AgentName.PLANNING: node1,
            AgentName.PLOT: node2,
        },
        event_bus=bus,
    )

    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
    await orch.run(ctx, start=AgentName.PLANNING)

    import asyncio
    # タスク実行を十分に待つ
    await asyncio.sleep(0.5)

    # started/completed イベント確認
    agents_seen = set(e.agent for e in received)
    assert "EventEmittingSkill" in agents_seen

    statuses = set(e.payload.get("status") for e in received if "status" in e.payload)
    assert "started" in statuses
    assert "completed" in statuses


@pytest.mark.asyncio
async def test_skill_error_event():
    """スキルエラー時に error イベントが発行されること"""
    bus = EventBus()
    received = []

    async def handler(event: AgentEvent):
        received.append(event)

    bus.subscribe("EventEmittingSkill", handler)

    skill = EventEmittingSkill(event_bus=bus, should_fail=True)
    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
    
    try:
        await skill.execute(ctx)
    except ValueError:
        pass

    import asyncio
    await asyncio.sleep(0.1)

    error_events = [e for e in received if e.payload.get("event") == "skill.error"]
    assert len(error_events) >= 1
    assert "Intentional failure" in error_events[0].payload.get("error", "")