import pytest
from src.agents.event_bus import EventBus, AgentEvent

@pytest.mark.asyncio
async def test_eventbus_publish_subscribe():
    bus = EventBus()
    received = []

    async def handler(event: AgentEvent):
        received.append(event.payload)

    bus.subscribe("test_agent", handler)
    await bus.publish_sync(AgentEvent(agent="test_agent", payload={"msg": "hello"}, correlation_id="1"))

    assert len(received) == 1
    assert received[0]["msg"] == "hello"