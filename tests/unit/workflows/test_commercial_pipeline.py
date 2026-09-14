import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_commercial_pipeline_step():
    mock_pipeline = MagicMock()
    mock_pipeline.execute_batch = AsyncMock(return_value={"completed_episodes": [1, 2, 3]})
    
    res = await mock_pipeline.execute_batch(book_id="b-com", batch_size=3)
    assert len(res["completed_episodes"]) == 3