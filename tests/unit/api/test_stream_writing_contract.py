"""執筆SSE の出力契約（フェーズ順序・Error 禁止・進捗単調性）を固定する回帰テスト。"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.backend.auth import get_current_user
from src.backend.routers import stream_writing
from src.backend.server import app

PHASE_ORDER = ["ContextBuilding", "Drafting", "Auditing", "Complete"]


def _events(body: str) -> list[dict]:
    out: list[dict] = []
    for chunk in body.split("data: ")[1:]:
        payload = chunk.split("\n\n")[0]
        try:
            out.append(json.loads(payload))
        except json.JSONDecodeError:
            continue
    return out


class _FakeChapters:
    async def get_chapter(self, branch_id: int, ep_num: int):
        return None

    async def create_chapter(self, **kwargs):
        return kwargs


class _FakeUow:
    def __init__(self) -> None:
        self.session = None
        self.chapters = _FakeChapters()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeEpisodeWriter:
    async def write(self, **kwargs):
        return {"text": "本文", "summary": "要約", "killer_phrase": "台詞"}


@pytest.fixture
def sse_env(monkeypatch):
    monkeypatch.setattr(stream_writing, "UnitOfWork", lambda db=None: _FakeUow())
    monkeypatch.setattr(
        stream_writing,
        "verify_book_ownership",
        AsyncMock(return_value=SimpleNamespace(id=1, user_id=1, genre="fantasy")),
    )
    monkeypatch.setattr(stream_writing, "EpisodeWriter", _FakeEpisodeWriter)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, role="user")
    yield
    app.dependency_overrides.pop(get_current_user, None)


async def _sse_body() -> str:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/stream/writing/1/1?branch_id=1")
    return resp.text


@pytest.mark.asyncio
async def test_sse_has_no_error_phase(sse_env):
    assert "Error" not in [e.get("phase") for e in _events(await _sse_body())]


@pytest.mark.asyncio
async def test_sse_phase_order_is_stable(sse_env):
    phases = [e.get("phase") for e in _events(await _sse_body())]
    it = iter(phases)
    assert all(any(p == expected for p in it) for expected in PHASE_ORDER)


@pytest.mark.asyncio
async def test_sse_progress_is_monotonic(sse_env):
    values = [e.get("progress") for e in _events(await _sse_body())]
    assert values == sorted(values)


@pytest.mark.asyncio
async def test_sse_uses_genre_from_verified_book(sse_env):
    """ジャンルが所有者検証で得た Book から渡されていることを確認する。"""
    stream_writing.verify_book_ownership.return_value = SimpleNamespace(  # type: ignore[attr-defined]
        id=1, user_id=1, genre="异世界恋爱"
    )
    captured: dict = {}
    original = _FakeEpisodeWriter.write

    async def _capture(self, **kwargs):
        captured.update(kwargs)
        return await original(self, **kwargs)

    _FakeEpisodeWriter.write = _capture  # type: ignore[method-assign]
    try:
        await _sse_body()
    finally:
        _FakeEpisodeWriter.write = original  # type: ignore[method-assign]

    assert captured["context"]["genre"] == "异世界恋爱"
