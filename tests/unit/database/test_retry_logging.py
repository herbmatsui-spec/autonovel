import sqlite3
import pytest
from unittest.mock import AsyncMock, patch
from src.backend.database.core import retry_with_logging

@pytest.mark.asyncio
async def test_retry_success_first_attempt():
    mock_func = AsyncMock(return_value="OK")
    decorated = retry_with_logging(retries=3, base_delay=0.01)(mock_func)

    res = await decorated()
    assert res == "OK"
    assert mock_func.call_count == 1

@pytest.mark.asyncio
async def test_retry_success_after_failure():
    # 1回目失敗、2回目に成功
    mock_func = AsyncMock(side_effect=[sqlite3.OperationalError("database is locked"), "RECOVERED"])
    decorated = retry_with_logging(retries=3, base_delay=0.001)(mock_func)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        res = await decorated()
        assert res == "RECOVERED"
        assert mock_func.call_count == 2

@pytest.mark.asyncio
async def test_retry_exhausted_raises_exception():
    # 全回数失敗
    mock_func = AsyncMock(side_effect=sqlite3.OperationalError("persistent lock"))
    decorated = retry_with_logging(retries=3, base_delay=0.001)(mock_func)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(sqlite3.OperationalError):
            await decorated()
        assert mock_func.call_count == 3
