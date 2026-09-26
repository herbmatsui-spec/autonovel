"""commercial_planning の静的ガード（同期Session・全削除・ハードコード の禁止）。"""
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "src/backend/routers/commercial_planning.py"


def test_router_does_not_use_sync_session():
    """async def で get_db（同期Session）を使わない。"""
    src = TARGET.read_text(encoding="utf-8")
    assert "Depends(get_db)" not in src


def test_router_does_not_delete_all_plots():
    src = TARGET.read_text(encoding="utf-8")
    assert ".delete()" not in src


def test_router_does_not_hardcode_branch_id_one_in_response():
    src = TARGET.read_text(encoding="utf-8")
    assert '"branch_id": 1' not in src


def test_router_uses_ssot_beat_model():
    src = TARGET.read_text(encoding="utf-8")
    assert "EpisodeBeat" in src
