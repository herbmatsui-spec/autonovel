"""`MultimediaService` の単体テスト。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.backend.config import settings
from src.backend.exceptions import MultimediaDisabledError
from src.backend.multimedia_service import (
    MultimediaResult,
    MultimediaService,
    make_minimal_series,
)


@pytest.fixture
def service(monkeypatch, tmp_path, real_db_manager):
    """Multimedia 有効化 + 一時出力ディレクトリのサービス。"""
    monkeypatch.setattr(settings, "ENABLE_MULTIMEDIA", True)
    return MultimediaService(output_dir=tmp_path / "mm")


def test_service_generate_media_mix(service, real_db_manager):
    result = service.generate_media_mix(book_id=1, format_name="manga")
    assert isinstance(result, MultimediaResult)
    assert result.asset_id is not None and result.asset_id > 0
    assert result.files
    assert any(f.endswith(".json") for f in result.files)
    assert result.metadata.get("format") == "manga"


def test_service_export_ebook(service, real_db_manager):
    result = service.export_ebook(book_id=2, formats=["epub", "pdf"])
    assert result.asset_id is not None and result.asset_id > 0
    # EPUB_AVAILABLE=False / PDF_AVAILABLE=False でも JSON fallback
    assert result.files
    assert result.metadata.get("formats")


def test_service_generate_if_routes_persists(service, real_db_manager):
    result, graph = service.generate_if_routes(book_id=3, persist=True)
    assert result.asset_id is not None and result.asset_id > 0
    assert graph is not None
    assert graph.entry_node_id


def test_service_generate_asset_pack(service, real_db_manager):
    result, task_id = service.generate_asset_pack(book_id=4)
    assert result.asset_id is not None and result.asset_id > 0
    assert task_id
    assert result.files
    zip_path = Path(result.files[0])
    assert zip_path.exists() and zip_path.suffix == ".zip"


def test_service_disabled_raises(monkeypatch, tmp_path, real_db_manager):
    monkeypatch.setattr(settings, "ENABLE_MULTIMEDIA", False)
    svc = MultimediaService(output_dir=tmp_path / "mm")
    with pytest.raises(MultimediaDisabledError):
        svc.generate_media_mix(book_id=1)


def test_get_artifact_round_trip(service, real_db_manager):
    result = service.generate_media_mix(book_id=5, format_name="manga")
    meta = service.get_artifact(result.asset_id)
    assert meta is not None
    assert meta["asset_type"] == "media_mix"
    assert meta["book_id"] == 5
    assert isinstance(meta["metadata"], dict)


def test_get_task_status(service, real_db_manager):
    _, task_id = service.generate_asset_pack(book_id=6)
    info = service.get_task(task_id)
    assert info is not None
    assert info["task_id"] == task_id
    assert info["status"] in {"completed", "running", "failed", "pending"}


def test_make_minimal_series_helper():
    s = make_minimal_series(episode_count=2)
    assert s.total_episodes == 2
    assert len(s.episodes) == 2
    assert all(ep.word_count > 0 for ep in s.episodes)
