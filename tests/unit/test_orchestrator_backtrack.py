# tests/unit/test_orchestrator_backtrack.py
"""Test suite for Orchestrator backtrack/retry mechanism fix.

This test reproduces the bug where audit failure causes AUDIT to re-execute
instead of transitioning back to WRITING.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.orchestrator import Orchestrator, AgentContext, AgentResult, AgentName


class MockWritingAgent:
    """Mock writing agent that can be controlled to pass/fail audit."""
    
    def __init__(self, should_pass_audit: bool = False):
        self.should_pass_audit = should_pass_audit
        self.call_count = 0
    
    async def __call__(self, ctx: AgentContext) -> AgentResult:
        self.call_count += 1
        # Simulate writing producing text
        ctx.artifacts["drafted_text"] = f"Chapter {ctx.ep_num} draft attempt {self.call_count}"
        return AgentResult(
            next_agent=AgentName.AUDIT,
            artifacts=ctx.artifacts,
            should_retry=False
        )


class MockAuditAgent:
    """Mock audit agent that fails first N times then passes."""
    
    def __init__(self, fail_count: int = 1):
        self.fail_count = fail_count
        self.call_count = 0
    
    async def __call__(self, ctx: AgentContext) -> AgentResult:
        self.call_count += 1
        
        # Simulate audit score
        if self.call_count <= self.fail_count:
            # Fail audit - should trigger backtrack to WRITING
            return AgentResult(
                next_agent=AgentName.WRITING,
                artifacts={
                    "audit_score": 60.0,
                    "audit_retry_count": ctx.artifacts.get("audit_retry_count", 0) + 1,
                    "regeneration_directive": "Improve character development",
                    "audit_status": "rejected",
                },
                should_retry=True,
                error=None
            )
        else:
            # Pass audit
            return AgentResult(
                next_agent=AgentName.ILLUSTRATION,
                artifacts={
                    "audit_score": 85.0,
                    "audit_status": "passed",
                },
                should_retry=False,
                error=None
            )


class MockIllustrationAgent:
    """Mock illustration agent."""
    
    def __init__(self):
        self.call_count = 0
    
    async def __call__(self, ctx: AgentContext) -> AgentResult:
        self.call_count += 1
        ctx.artifacts["illustrations"] = ["illustration_1.png"]
        return AgentResult(
            next_agent=None,
            artifacts=ctx.artifacts,
            should_retry=False
        )


@pytest.mark.asyncio
async def test_backtrack_from_audit_to_writing():
    """Test that audit failure correctly backtracks to WRITING (not re-execute AUDIT).
    
    This is the MAIN BUG REPRODUCTION TEST.
    Before fix: AUDIT re-executes itself infinitely
    After fix: AUDIT -> WRITING -> AUDIT -> ILLUSTRATION
    """
    writing_agent = MockWritingAgent()
    audit_agent = MockAuditAgent(fail_count=1)  # Fail once, then pass
    illustration_agent = MockIllustrationAgent()
    
    nodes = {
        AgentName.WRITING: writing_agent,
        AgentName.AUDIT: audit_agent,
        AgentName.ILLUSTRATION: illustration_agent,
    }
    
    orchestrator = Orchestrator(nodes=nodes)
    
    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
    result_ctx = await orchestrator.run(ctx, start=AgentName.WRITING)
    
    # Verify the flow: WRITING -> AUDIT (fail) -> WRITING -> AUDIT (pass) -> ILLUSTRATION
    assert writing_agent.call_count == 2, f"Expected WRITING called 2 times, got {writing_agent.call_count}"
    assert audit_agent.call_count == 2, f"Expected AUDIT called 2 times, got {audit_agent.call_count}"
    assert illustration_agent.call_count == 1, f"Expected ILLUSTRATION called 1 time, got {illustration_agent.call_count}"
    
    # Verify final state
    assert result_ctx.artifacts.get("audit_status") == "passed"
    assert result_ctx.artifacts.get("audit_score") == 85.0


@pytest.mark.asyncio
async def test_backtrack_max_limit_exceeded():
    """Test that exceeding max_backtracks_per_node falls through safely."""
    writing_agent = MockWritingAgent()
    audit_agent = MockAuditAgent(fail_count=10)  # Always fail
    illustration_agent = MockIllustrationAgent()
    
    nodes = {
        AgentName.WRITING: writing_agent,
        AgentName.AUDIT: audit_agent,
        AgentName.ILLUSTRATION: illustration_agent,
    }
    
    orchestrator = Orchestrator(nodes=nodes, max_backtracks_per_node=3)
    
    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
    
    # Should not raise an exception; should proceed to illustration agent safely
    result_ctx = await orchestrator.run(ctx, start=AgentName.WRITING)
    
    # Verify WRITING was called max_backtracks_per_node + 1 times (initial + retries)
    assert writing_agent.call_count == 4, f"WRITING called {writing_agent.call_count} times, expected 4"
    # Verify AUDIT was called max_backtracks_per_node + 1 times
    assert audit_agent.call_count == 4, f"AUDIT called {audit_agent.call_count} times, expected 4"
    # Verify ILLUSTRATION was called once
    assert illustration_agent.call_count == 1, f"ILLUSTRATION called {illustration_agent.call_count} time, expected 1"
    
    # Verify final state: we proceeded to illustration agent
    assert result_ctx.artifacts.get("illustrations") == ["illustration_1.png"]
    # Verify that we have the max backtrack exceeded flag set for the audit agent
    assert result_ctx.artifacts.get("audit_max_backtrack_exceeded") == True


@pytest.mark.asyncio
async def test_backtrack_history_recorded():
    """Test that backtrack history is recorded in AgentContext."""
    # TODO: Enable after Step 3 (backtrack_history field) and Step 10 (history recording) are implemented
    pytest.skip("Depends on backtrack_history field and recording logic")
    writing_agent = MockWritingAgent()
    audit_agent = MockAuditAgent(fail_count=1)
    illustration_agent = MockIllustrationAgent()
    
    nodes = {
        AgentName.WRITING: writing_agent,
        AgentName.AUDIT: audit_agent,
        AgentName.ILLUSTRATION: illustration_agent,
    }
    
    orchestrator = Orchestrator(nodes=nodes)
    
    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
    result_ctx = await orchestrator.run(ctx, start=AgentName.WRITING)
    
    # Check backtrack history exists
    assert "backtrack_history" in result_ctx.artifacts
    history = result_ctx.artifacts["backtrack_history"]
    assert len(history) == 1
    assert history[0]["from_node"] == "audit"
    assert history[0]["to_node"] == "writing"
    assert history[0]["reason"] == "audit_failed"


@pytest.mark.asyncio
async def test_backtrack_event_published():
    """Test that agent.backtracked event is published on backtrack."""
    # TODO: Enable after Step 6 (agent.backtracked event) and Step 12 (event publishing) are implemented
    pytest.skip("Depends on agent.backtracked event and publishing logic")
    writing_agent = MockWritingAgent()
    audit_agent = MockAuditAgent(fail_count=1)
    illustration_agent = MockIllustrationAgent()
    
    nodes = {
        AgentName.WRITING: writing_agent,
        AgentName.AUDIT: audit_agent,
        AgentName.ILLUSTRATION: illustration_agent,
    }
    
    # Mock event bus
    mock_event_bus = MagicMock()
    mock_event_bus.publish_async = AsyncMock()
    
    orchestrator = Orchestrator(nodes=nodes, event_bus=mock_event_bus)
    
    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
    await orchestrator.run(ctx, start=AgentName.WRITING)
    
    # Verify backtrack event was published
    backtrack_calls = [
        call for call in mock_event_bus.publish_async.call_args_list
        if call[0][0].payload.get("status") == "backtracked"
    ]
    assert len(backtrack_calls) == 1, "Expected exactly one backtracked event"
    
    event = backtrack_calls[0][0][0]
    assert event.agent == "audit"
    assert event.payload["target"] == "writing"


@pytest.mark.asyncio
async def test_agent_result_is_backtrack_field():
    """Test that AgentResult has is_backtrack field."""
    # TODO: Enable after Step 2 (is_backtrack field) is implemented
    pytest.skip("Depends on is_backtrack field in AgentResult")
    result = AgentResult(
        next_agent=AgentName.WRITING,
        artifacts={},
        should_retry=True,
        is_backtrack=True
    )
    assert result.is_backtrack is True
    
    # Default should be False
    result2 = AgentResult(next_agent=AgentName.WRITING, artifacts={})
    assert result2.is_backtrack is False


@pytest.mark.asyncio
async def test_agent_context_has_backtrack_history():
    """Test that AgentContext has backtrack_history field."""
    # TODO: Enable after Step 3 (backtrack_history field) is implemented
    pytest.skip("Depends on backtrack_history field in AgentContext")
    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
    # Should be able to set and get backtrack_history
    ctx.artifacts["backtrack_history"] = [{"from": "audit", "to": "writing"}]
    assert "backtrack_history" in ctx.artifacts


@pytest.mark.asyncio
async def test_self_repair_scenario():
    """Test that the writing agent uses regeneration directive to self-repair and pass audit.
    
    This test verifies the self-repair loop:
    1. Writing agent produces draft without improvement.
    2. Audit agent fails and provides regeneration directive.
    3. Orchestrator backtracks to writing agent with directive in context.
    4. Writing agent uses directive to produce improved draft.
    5. Audit agent passes improved draft.
    6. Flow proceeds to illustration.
    """
    # Mock writing agent that checks for regeneration directive
    class SelfRepairWritingAgent:
        def __init__(self):
            self.call_count = 0
            self.last_directive = None

        async def __call__(self, ctx: AgentContext) -> AgentResult:
            self.call_count += 1
            # Check if we have a regeneration directive from audit
            directive = ctx.artifacts.get("regeneration_directive")
            if directive:
                self.last_directive = directive
                # Produce improved draft that includes the directive keyword
                ctx.artifacts["drafted_text"] = f"Improved chapter {ctx.ep_num}: {directive}"
            else:
                # First attempt: draft without improvement
                ctx.artifacts["drafted_text"] = f"Chapter {ctx.ep_num} initial draft"
            return AgentResult(
                next_agent=AgentName.AUDIT,
                artifacts=ctx.artifacts,
                should_retry=False
            )

    # Mock audit agent that checks for improvement in draft
    class ImprovementCheckingAuditAgent:
        def __init__(self, require_improvement: bool = True):
            self.require_improvement = require_improvement
            self.call_count = 0

        async def __call__(self, ctx: AgentContext) -> AgentResult:
            self.call_count += 1
            draft = ctx.artifacts.get("drafted_text", "")

            # Check if draft contains improvement (simplified: contains "Improved")
            has_improvement = "Improved" in draft

            if self.require_improvement and not has_improvement:
                # Fail audit, provide regeneration directive
                return AgentResult(
                    next_agent=AgentName.WRITING,
                    artifacts={
                        "audit_score": 60.0,
                        "audit_retry_count": ctx.artifacts.get("audit_retry_count", 0) + 1,
                        "regeneration_directive": "Improve character development",
                        "audit_status": "rejected",
                    },
                    should_retry=True,
                    error=None
                )
            else:
                # Pass audit
                return AgentResult(
                    next_agent=AgentName.ILLUSTRATION,
                    artifacts={
                        "audit_score": 85.0,
                        "audit_status": "passed",
                    },
                    should_retry=False,
                    error=None
                )

    class MockIllustrationAgent:
        def __init__(self):
            self.call_count = 0

        async def __call__(self, ctx: AgentContext) -> AgentResult:
            self.call_count += 1
            ctx.artifacts["illustrations"] = ["illustration_1.png"]
            return AgentResult(
                next_agent=None,
                artifacts=ctx.artifacts,
                should_retry=False
            )

    writing_agent = SelfRepairWritingAgent()
    audit_agent = ImprovementCheckingAuditAgent(require_improvement=True)
    illustration_agent = MockIllustrationAgent()

    nodes = {
        AgentName.WRITING: writing_agent,
        AgentName.AUDIT: audit_agent,
        AgentName.ILLUSTRATION: illustration_agent,
    }

    orchestrator = Orchestrator(nodes=nodes)

    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1, artifacts={})
    result_ctx = await orchestrator.run(ctx, start=AgentName.WRITING)

    # Verify the flow: WRITING (fail) -> AUDIT -> WRITING (improved) -> AUDIT (pass) -> ILLUSTRATION
    assert writing_agent.call_count == 2, f"Expected WRITING called 2 times, got {writing_agent.call_count}"
    assert audit_agent.call_count == 2, f"Expected AUDIT called 2 times, got {audit_agent.call_count}"
    assert illustration_agent.call_count == 1, f"Expected ILLUSTRATION called 1 time, got {illustration_agent.call_count}"

    # Verify that the writing agent used the directive on the second call
    assert writing_agent.last_directive == "Improve character development", \
        f"Expected directive 'Improve character development', got {writing_agent.last_directive}"

    # Verify final state
    assert result_ctx.artifacts.get("audit_status") == "passed"
    assert result_ctx.artifacts.get("audit_score") == 85.0
    # Verify the final draft contains the improvement
    assert "Improved" in result_ctx.artifacts.get("drafted_text", "")
