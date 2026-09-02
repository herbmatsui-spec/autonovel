"""SSE ストリーミング生成エンドポイントの統合テスト (Step 15-17)。

検証対象: GET /easy_mode/generate/stream
- 正常系: start / chunk / done イベントが順序通りに返る
- 切断検知: クライアント切断時に adapter.cancel() が呼ばれる
- レート制限: 同一 IP から短時間に大量リクエストが来ると 429 を返す
"""
from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient


def _b64(payload: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _parse_sse_events(text: str) -> list[dict]:
    events: list[dict] = []
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        try:
            events.append(json.loads(line[len("data:") :].strip()))
        except json.JSONDecodeError:
            continue
    return events


def test_stream_emits_start_chunks_done(client: TestClient) -> None:
    """GET /easy_mode/generate/stream 正常系: start → chunk* → done."""
    payload = _b64(
        {
            "current_chapter": "森の奥で主人公は剣を抜いた。",
            "chapter_history": [],
            "character_params": {},
            "content_length_limit": 2000,
        }
    )
    resp = client.get(f"/easy_mode/generate/stream?payload={payload}")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert resp.headers.get("x-accel-buffering") == "no"

    events = _parse_sse_events(resp.text)
    types = [e.get("type") for e in events]
    assert types[0] == "start"
    assert "chunk" in types
    assert types[-1] == "done"
    chunks = [e for e in events if e.get("type") == "chunk"]
    assert len(chunks) >= 1


def test_stream_invokes_cancel_on_disconnect(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """クライアント切断時に adapter.cancel() が呼ばれる。

    ``request.is_disconnected`` は starlette の内部 ``receive`` チャネルを
    消費するため TestClient 上では再現が難しいため、ここでは generator 内
    のロジックで ``disconnect_check`` を強制的に True 返すモンキーパッチを
    あてる経路 (``src.backend.routers.streaming`` 名前空間) で検証する。
    """
    import src.backend.routers.streaming as streaming_module

    async def _always_disconnected(_request: object) -> bool:
        return True

    monkeypatch.setattr(streaming_module, "_check_disconnect", _always_disconnected)

    from src.services.llm.mock_adapter import MockLLMAdapter

    cancel_called = {"n": 0}

    class _SpyAdapter(MockLLMAdapter):
        def cancel(self) -> None:
            cancel_called["n"] += 1
            super().cancel()

    monkeypatch.setattr(streaming_module, "get_llm_adapter", lambda: _SpyAdapter())

    from src.backend.rate_limit import stream_limiter

    stream_limiter.reset()

    payload = _b64(
        {
            "current_chapter": "切断テスト",
            "chapter_history": [],
            "character_params": {},
            "content_length_limit": 2000,
        }
    )

    resp = client.get(f"/easy_mode/generate/stream?payload={payload}")
    assert resp.status_code == 200

    assert cancel_called["n"] >= 1


def test_stream_rate_limit(client: TestClient) -> None:
    """同一 IP から 4 回以上リクエストすると 429 が返る。"""
    from src.backend.rate_limit import stream_limiter

    stream_limiter.reset()
    payload = _b64(
        {
            "current_chapter": "RL",
            "chapter_history": [],
            "character_params": {},
            "content_length_limit": 2000,
        }
    )

    statuses: list[int] = []
    for _ in range(4):
        r = client.get(f"/easy_mode/generate/stream?payload={payload}")
        statuses.append(r.status_code)

    assert statuses[0] == 200
    assert 429 in statuses
