"""
tests/unit/test_foreshadow_orchestration.py - Foreshadow Lifecycle Orchestration & Sentinel Tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import csv

from novel_50ep.foreshadow_manager import ForeshadowItem, ForeshadowManager
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.backend.routers.narrative import router as narrative_router

app = FastAPI()
app.include_router(narrative_router)


def test_foreshadow_manager_stale_and_unresolved():
    """ForeshadowManager の未回収伏線取得および放置（Stale）検知テスト"""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = Path(tmpdir) / "foreshadow.csv"
        cliffs_path = Path(tmpdir) / "cliffs.txt"
        fm = ForeshadowManager(csv_path=csv_path, cliffs_path=cliffs_path)

        # 伏線追加
        fm.add_foreshadow(ep=1, f_type="伏線", text="胸元の光の石が黒く染まる", status="未回収")
        fm.add_foreshadow(ep=2, f_type="伏線", text="謎の仮面の男の忠告", status="未回収")
        fm.add_foreshadow(ep=3, f_type="伏線", text="幼少期の古文書", status="回収")

        unresolved = fm.get_unresolved_foreshadows()
        assert len(unresolved) == 2

        # 5話時点で第1話の伏線（4話経過）は threshold=5 では stale でない
        stale_ep5 = fm.get_stale_foreshadows(current_ep=5, threshold=5)
        assert len(stale_ep5) == 0

        # 6話時点で第1話の伏線（5話経過）は threshold=5 で stale となる
        stale_ep6 = fm.get_stale_foreshadows(current_ep=6, threshold=5)
        assert len(stale_ep6) == 1
        assert stale_ep6[0].ep == 1
        assert "胸元の光の石" in stale_ep6[0].text


def test_foreshadow_sentinel_api():
    """GET /api/narrative/{book_id}/{branch_id}/foreshadow/sentinel API テスト"""
    client = TestClient(app)

    with patch("novel_50ep.foreshadow_manager.ForeshadowManager.load_all") as mock_load:
        mock_load.return_value = [
            ForeshadowItem(ep=1, type="伏線", text="古い指輪の紋章", status="未回収"),
            ForeshadowItem(ep=5, type="伏線", text="森の奥の遺跡", status="未回収"),
        ]

        response = client.get("/api/narrative/1/1/foreshadow/sentinel?current_ep=7&threshold=5")
        assert response.status_code == 200
        data = response.json()

        assert data["book_id"] == 1
        assert data["current_ep"] == 7
        assert data["total_unresolved"] == 2
        assert data["stale_count"] == 1
        assert data["requires_rebuild"] is True
        assert len(data["stale_foreshadows"]) == 1
        assert data["stale_foreshadows"][0]["ep"] == 1


def test_plot_rebuild_api():
    """POST /api/narrative/{book_id}/{branch_id}/plot/rebuild API テスト"""
    client = TestClient(app)

    mock_app = MagicMock()
    mock_app.ainvoke = AsyncMock(return_value={
        "parsed_plots": [
            {
                "ep_num": 5,
                "title": "ペンダントの覚醒",
                "summary": "第1話のペンダントの謎が解き明かされる",
                "assigned_foreshadows": ["【最優先放置伏線】闇のペンダント"],
            }
        ],
        "quality_score": 0.9,
        "is_approved": True,
    })

    mock_sse = MagicMock()
    mock_sse.broadcast = AsyncMock()

    with patch("novel_50ep.foreshadow_manager.ForeshadowManager.load_all") as mock_load, \
         patch("src.backend.workflows.graphs.plot_graph.compile_plot_graph", return_value=mock_app), \
         patch("src.backend.routers.narrative.get_sse_manager", return_value=mock_sse):
        
        mock_load.return_value = [
            ForeshadowItem(ep=1, type="伏線", text="闇のペンダント", status="未回収"),
        ]

        payload = {
            "current_ep": 5,
            "target_episodes": 3,
            "genre": "ダークファンタジー",
            "theme": "復讐劇",
        }

        response = client.post("/api/narrative/1/1/plot/rebuild", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["current_ep"] == 5
        assert len(data["parsed_plots"]) == 1
        assert "【最優先放置伏線】闇のペンダント" in data["parsed_plots"][0]["assigned_foreshadows"]
