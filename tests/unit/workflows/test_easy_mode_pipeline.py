from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

from src.easy_mode.pipeline import EasyModePipeline


@pytest.mark.asyncio
async def test_easy_mode_pipeline_execute_default():
    pipeline = EasyModePipeline()
    res = await pipeline.execute(theme="悪役令嬢転生記")
    assert res["status"] == "done"
    assert res["theme"] == "悪役令嬢転生記"
    assert "book_id" in res


@pytest.mark.asyncio
async def test_easy_mode_pipeline_custom_run():
    pipeline = EasyModePipeline()
    pipeline.run = AsyncMock(return_value={"status": "custom_done", "theme": "SF"})

    res = await pipeline.execute(theme="SF")
    assert res["status"] == "custom_done"
    assert res["theme"] == "SF"
    pipeline.run.assert_awaited_once_with(theme="SF")
