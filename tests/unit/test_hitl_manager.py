"""
tests/unit/test_hitl_manager.py - Unit tests for HITLManager suspend, resume, and timeout auto-resume
"""

import asyncio
import pytest
from src.backend.hitl_manager import HITLManager
from src.shared.domain_event_bus import get_domain_event_bus


@pytest.mark.asyncio
async def test_hitl_manager_suspend_and_resume():
    manager = HITLManager()
    session_id = "test-session-001"

    received_events = []
    bus = get_domain_event_bus()
    bus.subscribe("HITL_SUSPENDED", lambda e: received_events.append(("SUSPENDED", e)))
    bus.subscribe("HITL_RESUMED", lambda e: received_events.append(("RESUMED", e)))

    # Start suspend in a background task
    async def run_suspend():
        return await manager.suspend(
            session_id=session_id,
            payload={"step": "generate_draft", "draft_preview": "Hello world"},
            timeout=5.0,
        )

    task = asyncio.create_task(run_suspend())

    # Wait shortly to ensure it entered suspend
    await asyncio.sleep(0.05)

    # Verify pending
    pending = manager.get_pending()
    assert any(p["session_id"] == session_id for p in pending)

    # Resume the session
    resumed = await manager.resume(
        session_id=session_id,
        response_data={
            "session_id": session_id,
            "approved": True,
            "feedback": "Approved with tweaks",
            "overrides": {"draft_content": "Modified Hello World"},
        },
    )
    assert resumed is True

    result = await task
    assert result["approved"] is True
    assert result["overrides"]["draft_content"] == "Modified Hello World"

    # Verify events
    assert any(ev[0] == "SUSPENDED" for ev in received_events)
    assert any(ev[0] == "RESUMED" for ev in received_events)

    # Pending list should now be empty for this session
    assert not any(p["session_id"] == session_id for p in manager.get_pending())


@pytest.mark.asyncio
async def test_hitl_manager_auto_resume_timeout():
    manager = HITLManager()
    session_id = "test-session-timeout"

    # Suspend with very short timeout
    result = await manager.suspend(
        session_id=session_id,
        payload={"step": "self_audit"},
        timeout=0.1,
    )

    assert result["session_id"] == session_id
    assert result["approved"] is True
    assert result["status"] == "auto_resumed_timeout"
    assert not any(p["session_id"] == session_id for p in manager.get_pending())


@pytest.mark.asyncio
async def test_hitl_manager_resume_unknown_session():
    manager = HITLManager()
    resumed = await manager.resume("non-existent-session", {"approved": True})
    assert resumed is False
