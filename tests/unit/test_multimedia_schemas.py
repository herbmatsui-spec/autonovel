"""`multimedia` スキーマの単体テスト。"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.backend.schemas.multimedia import (
    AssetPackRequest,
    EbookExportRequest,
    IFRouteGenerateRequest,
    MediaMixRequest,
    TaskStatusResponse,
)


def test_media_mix_request_defaults():
    req = MediaMixRequest(book_id=1)
    assert req.format == "manga"
    assert req.episode_num is None
    assert req.include_metadata is True


def test_ebook_export_request_defaults():
    req = EbookExportRequest(book_id=2)
    assert "epub" in req.formats
    assert "pdf" in req.formats


def test_asset_pack_request_defaults():
    req = AssetPackRequest(book_id=3)
    assert req.include_if_routes is True
    assert req.include_media_mix is True
    assert req.include_ebook is True


def test_media_mix_request_missing_book_id_raises():
    with pytest.raises(ValidationError):
        MediaMixRequest()  # type: ignore[call-arg]


def test_media_mix_request_invalid_book_id_raises():
    with pytest.raises(ValidationError):
        MediaMixRequest(book_id=0)


def test_if_route_generate_request_persist_default():
    req = IFRouteGenerateRequest(book_id=4)
    assert req.persist is True


def test_task_status_response_default_status():
    resp = TaskStatusResponse(task_id="abc")
    assert resp.status == "pending"
