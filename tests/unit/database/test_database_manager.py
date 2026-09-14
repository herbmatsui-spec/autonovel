import pytest
from src.backend.database.core import DatabaseManager

def test_database_manager_sqlite_init():
    mgr = DatabaseManager("sqlite:///storage/test.db", pool_size=5)
    assert mgr.db_path == "sqlite:///storage/test.db"
    assert mgr._pool_size == 5

def test_database_manager_null_pool_env(monkeypatch):
    monkeypatch.setenv("USE_NULL_POOL", "1")
    mgr = DatabaseManager("sqlite:///storage/test.db")
    assert mgr is not None
