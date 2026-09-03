"""Episode 6 S71: WebSocket E2E テスト."""
from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.core import get_db_manager
from src.backend.database.models import Base, Book


@pytest.fixture
def client():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    class _Mgr:
        def __init__(self):
            self.session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

        def get_session(self):
            return self.session_factory()

    import src.backend.database.core as core_mod
    core_mod.get_db_manager = lambda: _Mgr()

    async def _setup():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with _Mgr().get_session() as s:
            b = Book(title="t", genre="g", concept="c", current_branch_id=1)
            s.add(b)
            await s.commit()

    asyncio.run(_setup())

    import src.backend.auth as auth_mod
    auth_mod.validate_api_key_or_raise = lambda: None

    from src.backend.routers import branches as bmod

    app = FastAPI()
    app.include_router(bmod.router)
    return TestClient(app)


def test_ws_flow(client):
    r = client.post("/api/branches/", json={"book_id": 1, "name": "main"})
    bid = r.json()["id"]
    graph = {
        "entry_node_id": "n1",
        "nodes": {
            "n1": {"id": "n1", "episode_num": 1, "content": "start", "branch_type": "choice",
                   "choices": [{"id": "c1", "text": "go", "target_node_id": "n2"}]},
            "n2": {"id": "n2", "episode_num": 2, "content": "end", "branch_type": "merge", "merge_target": "n2"},
        },
    }
    client.put(f"/api/branches/1/graph?branch_id={bid}", json=graph)

    sid = client.post("/api/branches/play", json={"book_id": 1, "branch_id": bid}).json()["session_id"]

    with client.websocket_connect(f"/api/branches/play/{sid}/ws") as ws:
        # initial state
        msg = ws.receive_json()
        assert msg["type"] == "state"
        assert msg["current_node_id"] == "n1"

        # choose
        ws.send_json({"action": "choose", "choice_id": "c1"})
        msg = ws.receive_json()
        assert msg["type"] == "state"
        assert msg["current_node_id"] == "n2"

        # save
        ws.send_json({"action": "save"})
        msg = ws.receive_json()
        assert msg["save_points_count"] == 1

        # load
        ws.send_json({"action": "load", "index": 0})
        msg = ws.receive_json()
        assert msg["current_node_id"] == "n2"

        # end
        ws.send_json({"action": "end"})
        msg = ws.receive_json()
        assert msg["type"] == "closed"