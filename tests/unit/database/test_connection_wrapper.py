import pytest
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy import text
from src.backend.database.core import DatabaseManager

def test_connection_context_manager():
    """Test that DatabaseManager.connection() returns an async context manager yielding AsyncConnection"""
    # Create a mock database manager
    db_manager = DatabaseManager("sqlite:///:memory:")
    
    # The connection method should return an async context manager
    conn_cm = db_manager.connection()
    assert hasattr(conn_cm, '__aenter__')
    assert hasattr(conn_cm, '__aexit__')

def test_begin_context_manager():
    """Test that DatabaseManager.begin() returns an async context manager yielding AsyncConnection with transaction"""
    # Create a mock database manager
    db_manager = DatabaseManager("sqlite:///:memory:")
    
    # The begin method should return an async context manager
    begin_cm = db_manager.begin()
    assert hasattr(begin_cm, '__aenter__')
    assert hasattr(begin_cm, '__aexit__')

@pytest.mark.asyncio
async def test_connection_yields_async_connection():
    """Test that the connection context manager yields a proper AsyncConnection"""
    db_manager = DatabaseManager("sqlite:///:memory:")
    
    async with db_manager.connection() as conn:
        # Should be an AsyncConnection
        assert isinstance(conn, AsyncConnection)
        # Should be able to execute a simple query
        result = await conn.execute(text("SELECT 1"))
        assert result is not None

@pytest.mark.asyncio
async def test_begin_yields_async_connection():
    """Test that the begin context manager yields a proper AsyncConnection with transaction"""
    db_manager = DatabaseManager("sqlite:///:memory:")
    
    async with db_manager.begin() as conn:
        # Should be an AsyncConnection
        assert isinstance(conn, AsyncConnection)
        # Should be able to execute a simple query
        result = await conn.execute(text("SELECT 1"))
        assert result is not None
