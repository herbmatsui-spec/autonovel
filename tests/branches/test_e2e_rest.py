"""Episode 6 S70: REST フルフロー E2E テスト.

Branch 作成 → fork → play → save/load → export → stats.
"""
from __future__ import annotations

import asyncio
import io
import os
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
    import tempfile
    from pathlib import Path
    import os
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from src.backend.database.core import get_db_manager
    from src.backend.database.models import Base

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    db_url = f"sqlite+aiosqlite:///{db_path}"

    test_engine = create_async_engine(db_url, connect_args={"check_same_thread": False})
    test_session_factory = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)

    # Override the database URL in the core module
    import src.backend.database.core as core_mod
    core_mod.DATABASE_URL = db_url
    # Override the get_db_manager to return a manager using our test engine
    class TestMgr:
        def __init__(self):
            self.session_factory = test_session_factory
        def get_session(self):
            return self.session_factory()
    core_mod.get_db_manager = lambda: TestMgr()

    # Create tables
    async def _setup():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        # Add a test book
        async with test_session_factory() as session:
            from src.backend.database.models import Book
            book = Book(title="t", genre="g", concept="c", current_branch_id=1)
            session.add(book)
            await session.commit()
    import asyncio
    asyncio.run(_setup())

    # Set test API key
    os.environ["ALLOWED_API_KEYS"] = "testkey"

    from src.backend.routers import branches as bmod
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(bmod.router)

    try:
        yield TestClient(app)
    finally:
        try:
            os.unlink(db_path)
        except Exception:
            pass


def test_full_rest_flow(client):
    # 1) Branch
    r = client.post("/api/branches/", json={"book_id": 1, "name": "main"}, params={"api_key": "testkey"})
    print(f"Response status: {r.status_code}", flush=True)
    print(f"Response body: {r.text}", flush=True)
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
    r = client.put("/api/branches/1/graph", json=graph, params={"api_key": "testkey", "branch_id": bid})
    print(f"Graph PUT response status: {r.status_code}", flush=True)
    print(f"Graph PUT response body: {r.text}", flush=True)
    assert r.status_code == 200

    # 3) Fork
    r = client.post("/api/branches/1/fork", json={"parent_id": bid, "name": "alt", "fork_ep_num": 1}, params={"api_key": "testkey"})
    print(f"Fork response status: {r.status_code}", flush=True)
    print(f"Fork response body: {r.text}", flush=True)
    assert r.status_code == 201
    bid2 = r.json()["id"]

    # alt にもグラフを設定（export で EPUB 生成するため）
    r = client.put("/api/branches/1/graph", json={
        "entry_node_id": "a1",
        "nodes": {
            "a1": {"id": "a1", "episode_num": 1, "content": "alt start", "branch_type": "merge", "merge_target": "a1"}
        },
    }, params={"api_key": "testkey", "branch_id": bid2})
    print(f"Alt branch graph PUT response status: {r.status_code}", flush=True)
    print(f"Alt branch graph PUT response body: {r.text}", flush=True)
    assert r.status_code == 200

    # 4) Play
    r = client.post("/api/branches/play", json={"book_id": 1, "branch_id": bid}, params={"api_key": "testkey"})
    assert r.status_code == 201
    sid = r.json()["session_id"]

    # 5) Choose
    r = client.post(f"/api/branches/play/{sid}/choose", json={"choice_id": "c1"}, params={"api_key": "testkey"})
    assert r.status_code == 200

    # 6) Save
    r = client.post(f"/api/branches/play/{sid}/save", params={"api_key": "testkey"})
    assert r.json()["save_points_count"] == 1

    # 7) Load
    r = client.post(f"/api/branches/play/{sid}/load?index=0", params={"api_key": "testkey"})
    assert r.json()["current_node_id"] == "n2"

    # 8) End
    r = client.post(f"/api/branches/play/{sid}/end", json={"status": "completed"}, params={"api_key": "testkey"})
    assert r.json()["status"] == "completed"

    # 9) Export ZIP
    r = client.get("/api/branches/1/export", params={"api_key": "testkey"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.endswith(".epub")]
        assert len(names) == 2  # main + alt

    # 10) Stats
    r = client.get("/api/branches/1/stats", params={"api_key": "testkey"})
    assert r.json()["branch_count"] == 2
    assert r.json()["session_total"] == 1
    assert r.json()["session_completed"] == 1

    # 11) Choices
    r = client.get("/api/branches/1/choices", params={"api_key": "testkey"})
    assert r.json()["choice_counts"]["c1"] == 1