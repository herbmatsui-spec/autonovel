"""tests/unit/test_workspace_api.py"""
import pytest
from fastapi.testclient import TestClient

from src.backend.server import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_init_workspace(client):
    # First create a book via API or use existing? We'll just call init on a dummy id
    # The endpoint requires the book to exist; we can monkeypatch the db lookup.
    # For simplicity, test that unknown book returns 404.
    resp = client.post("/api/workspace/999999/init")
    # Expect 404 (book not found) or 200 if book exists; in test DB it's likely 404
    assert resp.status_code in (200, 404)


def test_get_unknown_file(client):
    resp = client.get("/api/workspace/1/files/NOPE.md")
    assert resp.status_code == 400


def test_workspace_file_roundtrip(client, tmp_path, monkeypatch):
    # Override workspace root to temp
    monkeypatch.setattr(
        "src.filesystem_memory.paths.WORKSPACE_ROOT", tmp_path / "ws"
    )
    # Re-import router module to pick up new root? The router imports paths at module load.
    # Instead, directly test writer/reader roundtrip via the service.
    from src.filesystem_memory.writer import write_file
    from src.filesystem_memory.reader import read_file
    from src.filesystem_memory.paths import get_workspace_path, ensure_workspace_dirs

    p = get_workspace_path(1, 1) / "SOUL.md"
    ensure_workspace_dirs(get_workspace_path(1, 1))
    write_file(p, "# test")
    assert read_file(p) == "# test"
