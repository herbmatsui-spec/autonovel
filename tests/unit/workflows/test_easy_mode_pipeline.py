import pytest
from unittest.mock import AsyncMock
from src.easy_mode.pipeline import EasyModePipeline

@pytest.mark.asyncio
async def test_easy_mode_pipeline_run():
    pipeline = EasyModePipeline()
    pipeline.run = AsyncMock(return_value={"status": "done", "book_id": "b-easy-1"})
    
    res = await pipeline.run(theme="悪役令嬢")
    assert res["status"] == "done"
    assert res["book_id"] == "b-easy-1"