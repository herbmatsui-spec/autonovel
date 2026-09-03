"""Episode 6 S70: REST フルフロー E2E テスト.

Branch 作成 → fork → play → save/load → export → stats.
"""
from __future__ import annotations

import asyncio
import io
import zipfile

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

    get_db_manager.__globals__["_orig"] = get_db_manager
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


def test_full_rest_flow(client):
    # 1) Branch
    r = client.post("/api/branches/", json={"book_id": 1, "name": "main"})
    assert r.status_code == 201
    bid = r.json()["id"]

    # 2) Graph PUT
    graph = {
        "entry_node_id": "n1",
        "nodes": {
            "n1": {"id": "n1", "episode_num": 1, "content": "start", "branch_type": "choice",
                   "choices": [{"id": "c1", "text": "go", "target_node_id": "n2"}]},
            "n2": {"id": "n2", "episode_num": 2, "content": "end", "branch_type": "merge", "merge_target": "n2"},
        },
    }
    r = client.put(f"/api/branches/1/graph?branch_id={bid}", json=graph)
    assert r.status_code == 200

    # 3) Fork
    r = client.post("/api/branches/1/fork", json={"parent_id": bid, "name": "alt", "fork_ep_num": 1})
    assert r.status_code == 201
    bid2 = r.json()["id"]

    # alt にもグラフを設定（export で EPUB 生成するため）
    client.put(
        f"/api/branches/1/graph?branch_id={bid2}",
        json={
            "entry_node_id": "a1",
            "nodes": {
                "a1": {"id": "a1", "episode_num": 1, "content": "alt start", "branch_type": "merge", "merge_target": "a1"}
            },
        },
    )

    # 4) Play
    r = client.post("/api/branches/play", json={"book_id": 1, "branch_id": bid})
    assert r.status_code == 201
    sid = r.json()["session_id"]

    # 5) Choose
    r = client.post(f"/api/branches/play/{sid}/choose", json={"choice_id": "c1"})
    assert r.status_code == 200

    # 6) Save
    r = client.post(f"/api/branches/play/{sid}/save")
    assert r.json()["save_points_count"] == 1

    # 7) Load
    r = client.post(f"/api/branches/play/{sid}/load?index=0")
    assert r.json()["current_node_id"] == "n2"

    # 8) End
    r = client.post(f"/api/branches/play/{sid}/end", json={"status": "completed"})
    assert r.json()["status"] == "completed"

    # 9) Export ZIP
    r = client.get("/api/branches/1/export")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.endswith(".epub")]
        assert len(names) == 2  # main + alt

    # 10) Stats
    r = client.get("/api/branches/1/stats")
    assert r.json()["branch_count"] == 2
    assert r.json()["session_total"] == 1
    assert r.json()["session_completed"] == 1

    # 11) Choices
    r = client.get("/api/branches/1/choices")
    assert r.json()["choice_counts"]["c1"] == 1