import pytest
import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.backend.routers.pipeline_stream import router as pipeline_router
from src.backend.websocket.pipeline_hub import pipeline_event_hub
from src.backend.schemas.pipeline_events import PipelineEvent

app = FastAPI()
app.include_router(pipeline_router)

def test_pipeline_websocket_and_hub():
    client = TestClient(app)

    ev = PipelineEvent(
        event_type="task_started",
        book_id=999,
        task_id="task_001",
        payload={"message": "Writing chapter 1"}
    )
    asyncio.run(pipeline_event_hub.broadcast(ev))

    with client.websocket_connect("/api/ws/pipeline/999") as websocket:
        data = websocket.receive_json()
        assert data["event_type"] == "task_started"
        assert data["book_id"] == 999
        assert data["task_id"] == "task_001"

        ev2 = PipelineEvent(
            event_type="score_updated",
            book_id=999,
            task_id="task_001",
            payload={"score": 82.5}
        )
        asyncio.run(pipeline_event_hub.broadcast(ev2))

        data2 = websocket.receive_json()
        assert data2["event_type"] == "score_updated"
        assert data2["payload"]["score"] == 82.5

def test_sse_pipeline_stream():
    client = TestClient(app)
    with client.stream("GET", "/api/stream/pipeline/999") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        # read first chunk (initial snapshot or ping)
        for chunk in response.iter_text():
            if chunk:
                assert "data:" in chunk or "ping" in chunk
                break
