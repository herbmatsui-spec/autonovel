"""Integration tests for conflict review and resolution API."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.conflicts import router, set_conflict_store
from src.fusion.models import Conflict
from src.pipeline.emotional_residue import EmotionType
from src.stores.conflict_store import ConflictStore


def test_resolve_conflict_manual(tmp_path):
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    conflict_file = tmp_path / "conflicts.jsonl"
    store = ConflictStore(conflict_file)
    set_conflict_store(store)

    # 矛盾をストアに追加
    c = Conflict(
        pair=("A", "D"),
        emotion=EmotionType.TRUST,
        sources=[("annotation", 0.7, 1.0), ("pipeline", -0.5, 0.5)],
    )
    store.record_conflicts([c], episode=15)

    # 1. 一覧取得
    resp = client.get("/api/conflicts?episode=15")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    conflict_id = data[0]["conflict_id"]

    # 2. 詳細取得
    resp = client.get(f"/api/conflicts/{conflict_id}")
    assert resp.status_code == 200
    assert resp.json()["conflict_id"] == conflict_id

    # 3. 手動解決 (manual_value = 0.6)
    resp = client.post(
        f"/api/conflicts/{conflict_id}/resolve",
        json={"resolution": "manual", "manual_value": 0.6},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"

    # ストアから解決済み情報を確認
    resolution = store.get_resolution(conflict_id)
    assert resolution is not None
    assert resolution["resolution"] == "manual"
    assert resolution["manual_value"] == 0.6
