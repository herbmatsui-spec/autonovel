import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.auto_workflow_pipeline import AutoWorkflowPipeline
from src.services.pipeline_base import WorkflowContext, WorkflowStep

@pytest.mark.asyncio
async def test_auto_workflow_pipeline_execute_steps():
    step1 = AsyncMock(spec=WorkflowStep)
    step1.execute.return_value = True
    
    step2 = AsyncMock(spec=WorkflowStep)
    step2.execute.return_value = False
    
    pipeline = AutoWorkflowPipeline(steps=[step1, step2])
    ctx = WorkflowContext(
        genre="ファンタジー",
        keywords="勇者",
        archetype_key="default",
        target_eps=1,
        initial_limit=1,
        word_count=1000,
        marketing_pack={}
    )
    engine = MagicMock()
    reporter = MagicMock()
    
    result = await pipeline.execute(ctx, engine, reporter)
    assert result.status in ("failed", "stopped")
    step1.execute.assert_awaited_once()
    step2.execute.assert_awaited_once()
