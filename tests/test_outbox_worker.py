import json

import pytest
from sqlalchemy import text

from src.backend.tasks import _process_outbox_events_async


@pytest.mark.asyncio
async def test_outbox_worker_success():
    # Setup test DB
    from config.container import Container
    db = Container.db()

    # Create the outbox table manually for tests to ensure isolated sqlite DB works
    async with db.get_session() as session:
        async with session.begin():
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
            # Clear existing events
            await session.execute(text("DELETE FROM outbox"))

            # Insert test events
            payload_add = {
                "collection": "test_collection",
                "id": "doc1",
                "content": "some content",
                "embedding": [0.1, 0.2],
                "metadata": {"key": "value"}
            }

            await session.execute(
                text("INSERT INTO outbox (event_type, payload, status) VALUES (:e, :p, :s)"),
                {"e": "chroma_add", "p": json.dumps(payload_add), "s": "pending"}
            )

    # Call the new outbox processing task
    await _process_outbox_events_async()

    # Verify statuses updated
    async with db.get_session() as session:
        result = await session.execute(text("SELECT * FROM outbox"))
        rows = result.mappings().fetchall()

    assert len(rows) == 1
    assert rows[0]["status"] == "done"
    assert rows[0]["processed_at"] is not None
