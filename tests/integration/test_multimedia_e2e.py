"""Multimedia end-to-end テスト (実サービス / 実ファイル出力)。"""
from __future__ import annotations

import io
import zipfile

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from src.backend import config
from src.backend.auth import validate_api_key_or_raise
from src.backend.database import SessionLocal
from src.backend.multimedia_service import MultimediaService
from src.backend.rate_limit import generate_limiter
from src.backend.routers import multimedia as multimedia_router


@pytest.fixture
def mm_e2e_client(monkeypatch, tmp_path, real_db_manager):
    monkeypatch.setattr(config.settings, "ENABLE_MULTIMEDIA", True)
    monkeypatch.setattr(config.settings, "MULTIMEDIA_OUTPUT_DIR", str(tmp_path / "mm"))

    service = MultimediaService(output_dir=tmp_path / "mm")

    app = FastAPI()
    app.include_router(multimedia_router.router, prefix="/multimedia", tags=["multimedia"])
    app.dependency_overrides[multimedia_router.get_multimedia_service] = lambda: service
    app.dependency_overrides[validate_api_key_or_raise] = lambda: "k"
    generate_limiter.reset()

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_asset_pack_e2e(mm_e2e_client):
    res = mm_e2e_client.post(
        "/multimedia/asset-pack",
        json={
            "book_id": 1,
            "include_if_routes": True,
            "include_media_mix": True,
            "include_ebook": True,
            "ebook_formats": ["epub", "pdf"],
            "media_mix_formats": ["manga"],
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    asset_id = body["asset_id"]
    assert asset_id > 0
    dl = mm_e2e_client.get(f"/multimedia/artifacts/{asset_id}/download")
    assert dl.status_code == 200
    assert dl.headers["content-type"].startswith("application/zip")
    with zipfile.ZipFile(io.BytesIO(dl.content)) as zf:
        names = zf.namelist()
    assert "bundle.json" in names


def test_media_mix_then_artifact_meta(mm_e2e_client):
    res = mm_e2e_client.post(
        "/multimedia/media-mix", json={"book_id": 2, "format": "manga"}
    )
    assert res.status_code == 200, res.text
    asset_id = res.json()["asset_id"]
    meta = mm_e2e_client.get(f"/multimedia/artifacts/{asset_id}")
    assert meta.status_code == 200
    assert meta.json()["asset_type"] == "media_mix"


def test_if_routes_persist(mm_e2e_client):
    res = mm_e2e_client.post("/multimedia/if-routes", json={"book_id": 3, "persist": True})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["nodes"] >= 1
    assert body["entry_node_id"]
