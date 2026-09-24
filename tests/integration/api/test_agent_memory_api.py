"""Integration tests for agent memory API."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.agent.memory.manager import MemoryManager
from src.api.agent_memory import router, set_agent_memory_manager


def test_core_memory_dump():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    manager = MemoryManager()
    manager.update_emotion("Hero", "Heroine", "affection", 0.75, reason="告白")
    set_agent_memory_manager(manager)

    # 1. CoreMemory ダンプ
    resp = client.get("/api/agent/memory/core")
    assert resp.status_code == 200
    data = resp.json()
    assert "character_emotions" in data
    assert data["character_emotions"]["Hero->Heroine"]["affection"] == 0.75

    # 2. Archival 統計
    resp_arch = client.get("/api/agent/memory/archival/stats")
    assert resp_arch.status_code == 200
    assert "total_entries" in resp_arch.json()

    # 3. 強制圧縮
    resp_compact = client.post("/api/agent/memory/compact")
    assert resp_compact.status_code == 200
    assert "compacted" in resp_compact.json()
