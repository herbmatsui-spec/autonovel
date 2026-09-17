import pytest
from sqlalchemy import text
from src.backend.database.core import (
    DatabaseManager,
    get_db_manager,
    set_db_manager,
    SessionLocal,
    engine,
)

def test_database_manager_sqlite_init():
    mgr = DatabaseManager("sqlite:///storage/test.db", pool_size=5)
    assert mgr.db_path == "sqlite:///storage/test.db"
    assert mgr._pool_size == 5

def test_database_manager_null_pool_env(monkeypatch):
    monkeypatch.setenv("USE_NULL_POOL", "1")
    mgr = DatabaseManager("sqlite:///storage/test.db")
    assert mgr is not None

def test_database_manager_postgresql_urls():
    mgr = DatabaseManager("postgresql://user:pass@localhost:5432/db")
    assert mgr is not None

@pytest.mark.asyncio
async def test_database_manager_in_memory_operations():
    mgr = DatabaseManager("sqlite+aiosqlite:///:memory:")

    # execute table creation
    await mgr.execute(text("CREATE TABLE test_table (id INTEGER PRIMARY KEY AUTOINCREMENT, val TEXT)"))

    # execute insert
    await mgr.execute(text("INSERT INTO test_table (val) VALUES (:v)"), {"v": "hello"})

    # fetch_one
    row = await mgr.fetch_one(text("SELECT * FROM test_table WHERE id = :id"), {"id": 1})
    assert row is not None
    assert row["val"] == "hello"

    # fetch_all
    rows = await mgr.fetch_all(text("SELECT * FROM test_table"))
    assert len(rows) == 1
    assert rows[0]["val"] == "hello"

    # fetch_lastrowid
    last_id = await mgr.fetch_lastrowid("INSERT INTO test_table (val) VALUES (?)", ("world",))
    assert last_id == 2

    # enqueue_write & flush_writes
    await mgr.enqueue_write(text("INSERT INTO test_table (val) VALUES (:v)"), {"v": "async_write"})
    await mgr.flush_writes()

    # get_session
    session = mgr.get_session()
    assert session is not None
    await session.close()

@pytest.mark.asyncio
async def test_database_manager_conn_operations():
    mgr = DatabaseManager("sqlite+aiosqlite:///:memory:")
    conn = await mgr.get_conn()
    assert conn is not None
    await mgr.release_read_conn(conn)

@pytest.mark.asyncio
async def test_database_manager_read_conn():
    mgr = DatabaseManager("sqlite+aiosqlite:///:memory:")
    conn = await mgr.get_read_conn()
    assert conn is not None
    await mgr.release_read_conn(conn)

@pytest.mark.asyncio
async def test_database_manager_save_internal_state(tmp_path):
    db_file = tmp_path / "internal_state_test.db"
    db_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    mgr = DatabaseManager(db_url)

    await mgr.execute(text("CREATE TABLE internal_state (id INTEGER PRIMARY KEY AUTOINCREMENT, key VARCHAR(255), value TEXT, updated_at DATETIME)"))

    # Insert new state
    await mgr.save_internal_state("test_key", "value_1")
    row = await mgr.fetch_one(text("SELECT value FROM internal_state WHERE key = 'test_key'"))
    assert row is not None
    assert row["value"] == "value_1"

    # Update existing state
    await mgr.save_internal_state("test_key", "value_2")
    row = await mgr.fetch_one(text("SELECT value FROM internal_state WHERE key = 'test_key'"))
    assert row is not None
    assert row["value"] == "value_2"

def test_get_and_set_db_manager():
    mgr = get_db_manager()
    assert mgr is not None

    set_db_manager(None)

def test_session_local_and_engine_proxies():
    # Calling proxy properties
    assert engine.name is not None
    assert callable(SessionLocal)
