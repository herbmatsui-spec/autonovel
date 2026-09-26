"""/commercial/planning の OpenAPI 契約テスト。"""
from __future__ import annotations

from src.backend.server import app


def _schema_for(path: str, method: str) -> dict:
    spec = app.openapi()
    return spec["paths"][path][method]


def test_get_beat_sheet_declares_episode_beat_fields():
    op = _schema_for("/commercial/planning/{book_id}", "get")
    ref = op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert ref.endswith("BeatSheetResponse")


def test_generate_response_declares_task_id():
    op = _schema_for("/commercial/planning/generate", "post")
    schema = op["responses"]["200"]["content"]["application/json"]["schema"]
    assert "$ref" in schema
    assert schema["$ref"].endswith("BeatSheetTaskResponse")
