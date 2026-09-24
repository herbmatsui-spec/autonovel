"""Integration tests for dashboard API."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dashboard import router, set_dashboard_engine
from src.fusion.engine import FusionEngine
from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.stores.vector_store import InMemoryVectorStore


def test_timeline_endpoint():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    store = InMemoryVectorStore()
    vec = EmotionalVector(episode_id="ep1")
    vec.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, 0.7, 1.0, "...", "ep1"))
    store.upsert("annotation", "ep1:A->B", vec)

    engine = FusionEngine(store)
    set_dashboard_engine(engine)

    resp = client.get("/api/dashboard/timeline?pair=A,B&from=1&to=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["labels"]) == 3
    assert len(data["datasets"]) >= 1
    assert data["datasets"][0]["label"] == "Fused (A,B)"
