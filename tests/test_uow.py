import json

import pytest
from sqlalchemy import text

from src.backend.database import UnitOfWork


@pytest.mark.asyncio
async def test_unit_of_work_commit():
    from config.container import Container
    db = Container.db()

    # テーブル初期化
    async with db.get_session() as session:
        async with session.begin():
            await session.execute(text("CREATE TABLE IF NOT EXISTS uow_test (id INTEGER PRIMARY KEY, val TEXT)"))
            await session.execute(text("DELETE FROM uow_test"))
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type VARCHAR(64) NOT NULL,
                    payload TEXT NOT NULL,
                    status VARCHAR(32) NOT NULL DEFAULT 'pending',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    processed_at DATETIME,
                    error_message TEXT
                )
            """))
            await session.execute(text("DELETE FROM outbox"))

    # 正常系コミットテスト
    async with UnitOfWork(db) as uow:
        conn = await uow.session.connection()
        await conn.exec_driver_sql("INSERT INTO uow_test (id, val) VALUES (?, ?)", (1, "hello"))
        uow.stage_chroma_add("test_col", "doc_uow", "uow content", [0.1, 0.2])

    # コミット後の確認
    async with db.get_session() as session:
        result = await session.execute(text("SELECT * FROM uow_test WHERE id=1"))
        row = result.mappings().fetchone()
        assert row is not None
        assert row["val"] == "hello"

        # Outboxに記録されているか確認
        outbox_result = await session.execute(text("SELECT * FROM outbox"))
        outbox_rows = outbox_result.mappings().fetchall()

    assert len(outbox_rows) == 1
    assert outbox_rows[0]["event_type"] == "chroma_add"
    payload = json.loads(outbox_rows[0]["payload"])
    assert payload["id"] == "doc_uow"

@pytest.mark.asyncio
async def test_unit_of_work_rollback():
    from config.container import Container
    db = Container.db()

    async with db.get_session() as session:
        async with session.begin():
            await session.execute(text("CREATE TABLE IF NOT EXISTS uow_test (id INTEGER PRIMARY KEY, val TEXT)"))
            await session.execute(text("DELETE FROM uow_test"))
            await session.execute(text("DELETE FROM outbox"))

    # 異常系ロールバックテスト
    try:
        async with UnitOfWork(db) as uow:
            conn = await uow.session.connection()
            await conn.exec_driver_sql("INSERT INTO uow_test (id, val) VALUES (?, ?)", (2, "failed"))
            uow.stage_chroma_add("test_col", "doc_failed", "failed content", [0.1])
            raise ValueError("Forced error to trigger rollback")
    except ValueError:
        pass

    # ロールバック後にデータが存在しないことを確認
    async with db.get_session() as session:
        result = await session.execute(text("SELECT * FROM uow_test WHERE id=2"))
        row = result.mappings().fetchone()
        assert row is None

        # Outboxにも記録されていないことを確認
        outbox_result = await session.execute(text("SELECT * FROM outbox"))
        outbox_rows = outbox_result.mappings().fetchall()

    assert len(outbox_rows) == 0
