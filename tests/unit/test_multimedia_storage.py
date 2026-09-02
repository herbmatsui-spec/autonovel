"""`multimedia_storage` の単体テスト。"""
from __future__ import annotations

from src.backend import config
from src.backend.multimedia_storage import ensure_multimedia_dir, get_multimedia_dir


def test_ensure_multimedia_dir_creates(monkeypatch, tmp_path):
    target = tmp_path / "mm"
    monkeypatch.setattr(config.settings, "MULTIMEDIA_OUTPUT_DIR", str(target))
    p = ensure_multimedia_dir()
    assert p.exists()
    assert p.is_dir()


def test_ensure_multimedia_dir_idempotent(monkeypatch, tmp_path):
    target = tmp_path / "mm"
    monkeypatch.setattr(config.settings, "MULTIMEDIA_OUTPUT_DIR", str(target))
    p1 = ensure_multimedia_dir()
    p2 = ensure_multimedia_dir()
    assert p1 == p2
    assert p1.exists()


def test_get_multimedia_dir_returns_path(monkeypatch, tmp_path):
    monkeypatch.setattr(config.settings, "MULTIMEDIA_OUTPUT_DIR", str(tmp_path / "x"))
    p = get_multimedia_dir()
    assert isinstance(p, type(tmp_path))
