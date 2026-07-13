from unittest.mock import AsyncMock, MagicMock

import pytest

from kernels.connection import ConnectionState
from kernels.connection_kernel import ConnectionKernel


class MockLLMEngine:
    def __init__(self):
        self.generate = AsyncMock()

class MockKernelEngine:
    def __init__(self):
        self.llm = MockLLMEngine()

@pytest.mark.asyncio
async def test_connection_kernel_stagnation_trigger():
    # Setup
    engine = MockKernelEngine()
    kernel = ConnectionKernel(engine)

    # Create a context that should trigger stagnation
    # Assuming ConnectionStagnationDetector looks for a lack of progress in connection_history
    class MockContext:
        connection_history = [
            ConnectionState(affection=10, trust=10, dependence=10),
            ConnectionState(affection=10, trust=10, dependence=10),
            ConnectionState(affection=10, trust=10, dependence=10),
            ConnectionState(affection=10, trust=10, dependence=10),
            ConnectionState(affection=10, trust=10, dependence=10),
        ]
        summary = "Two characters talking in a cafe."
        characters = ["CharA", "CharB"]
        connection_state = ConnectionState(resonance=10, trust=10)
        analytics = MagicMock()
        analytics.is_connection_event = False
        global_state = {}

    context = MockContext()

    # Mock LLM response for generation, polish, and audit
    # 1. generate_resonance_event -> generate
    # 2. apply_resonance_polish -> generate
    # 3. _run_connection_audit -> generate
    engine.llm.generate.side_effect = [
        "Initial scene proposal...",
        "Polished scene proposal...",
        "APPROVED\nReasoning: Bond growth is earned."
    ]

    result = await kernel.execute(context)

    assert result is not None
    assert "scene_proposal" in result
    assert "analytics_update" in result
    assert engine.llm.generate.call_count == 3

@pytest.mark.asyncio
async def test_connection_kernel_no_trigger():
    engine = MockKernelEngine()
    kernel = ConnectionKernel(engine)

    class MockContext:
        connection_history = []
        analytics = MagicMock()
        analytics.is_connection_event = False
        global_state = {}

    context = MockContext()
    result = await kernel.execute(context)

    assert result is None
    engine.llm.generate.assert_not_called()
