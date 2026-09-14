import pytest
from unittest.mock import MagicMock, AsyncMock
from src.backend.database.core import DatabaseConnectionWrapper

def test_wrapper_delegation():
    mock_sql_conn = MagicMock()
    mock_dbapi_conn = MagicMock()
    mock_dbapi_conn.fetchone.return_value = ("row1",)
    mock_dbapi_conn.fetchall.return_value = [("row1",), ("row2",)]
    
    wrapper = DatabaseConnectionWrapper(mock_sql_conn, mock_dbapi_conn)
    
    wrapper.execute("SELECT 1")
    mock_dbapi_conn.execute.assert_called_once_with("SELECT 1", ())
    
    assert wrapper.fetchone() == ("row1",)
    assert wrapper.fetchall() == [("row1",), ("row2",)]
    
    wrapper.commit()
    mock_dbapi_conn.commit.assert_called_once()
    
    wrapper.rollback()
    mock_dbapi_conn.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_wrapper_close_handles_rollback():
    mock_sql_conn = AsyncMock()
    mock_dbapi_conn = MagicMock()
    
    wrapper = DatabaseConnectionWrapper(mock_sql_conn, mock_dbapi_conn)
    await wrapper.close()
    
    mock_dbapi_conn.rollback.assert_called_once()
    mock_sql_conn.close.assert_awaited_once()
