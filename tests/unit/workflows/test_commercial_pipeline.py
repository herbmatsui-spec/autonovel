from __future__ import annotations

import pytest

from src.core.exceptions import PipelineError
from src.backend.workflows.commercial_pipeline import CommercialPipeline, async_retry


@pytest.mark.asyncio
async def test_commercial_pipeline_async_retry_success():
    call_count = 0

    @async_retry(max_attempts=3, base_delay=0.01)
    async def flaky_task():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("temporary error")
        return "success"

    result = await flaky_task()
    assert result == "success"
    assert call_count == 2


@pytest.mark.asyncio
async def test_commercial_pipeline_async_retry_permanent_failure():
    @async_retry(max_attempts=2, base_delay=0.01)
    async def always_failing_task():
        raise RuntimeError("always fail")

    with pytest.raises(PipelineError):
        await always_failing_task()


def test_commercial_pipeline_init():
    pipeline = CommercialPipeline(csv_path="output/test.csv")
    assert pipeline.csv_path == "output/test.csv"
    assert hasattr(pipeline, "execute_batch")
