import os
import sys
sys.path.insert(0, os.path.abspath("."))

import pytest
from fastapi.testclient import TestClient

from src.backend.server import app
from src.schemas.ux_schemas import (
    HeatmapData,
    AffinityData,
    SceneTheme,
    WhatIfRequest,
    ReadingSpeedData,
    GapMoePreference,
)
from src.services.metrics_analyzer import MetricsAnalyzer
from src.services.affinity_tracker import AffinityTracker
from src.services.pacing_adjuster import PacingAdjuster
from src.services.preference_store import PreferenceStore


def test_metrics_analyzer_heatmap():
    analyzer = MetricsAnalyzer()
    text = "敵が迫り緊迫する中、主人公は怒号をあげて剣を振るった。激痛が走り、殺気が満ちる。"
    heatmap = analyzer.analyze_text(text, episode_id="test_ep", title="緊迫バトル")
    assert isinstance(heatmap, HeatmapData)
    assert len(heatmap.points) > 0
    assert heatmap.points[0].tension >= 0.0


def test_affinity_tracker():
    tracker = AffinityTracker()
    text = "「ありがとう、あなたと一緒にいられて本当に嬉しい」と彼女は笑顔で赤面した。"
    affinities = tracker.update_from_text(text, character_name="メインヒロイン")
    assert len(affinities) >= 1
    main_heroine = next(a for a in affinities if a.character_name == "メインヒロイン")
    assert main_heroine.affinity_score > 60.0


def test_pacing_adjuster():
    adjuster = PacingAdjuster()
    fast_data = ReadingSpeedData(chars_read=1000, duration_ms=5000, scroll_speed_px_per_sec=450)
    density_fast = adjuster.calculate_density(fast_data)
    assert density_fast <= 30

    slow_data = ReadingSpeedData(chars_read=1000, duration_ms=60000, scroll_speed_px_per_sec=50)
    density_slow = adjuster.calculate_density(slow_data)
    assert density_slow >= 65


def test_preference_store():
    store = PreferenceStore()
    pref = GapMoePreference(gap_type="kuudere_passionate", intensity=85)
    store.save_preference("user_123", pref)
    loaded = store.get_preference("user_123")
    assert loaded.gap_type == "kuudere_passionate"
    prompt = store.build_custom_gap_prompt("user_123")
    assert "独占欲" in prompt


def test_ux_api_endpoints():
    client = TestClient(app)

    def extract_data(response):
        js = response.json()
        if isinstance(js, dict) and "data" in js:
            return js["data"]
        return js

    # 1. Heatmap
    res = client.get("/api/ux/heatmap?title=Test&text_sample=激しい戦い")
    assert res.status_code == 200
    assert "points" in extract_data(res)

    # 2. Affinity
    res = client.get("/api/ux/affinity")
    assert res.status_code == 200
    assert isinstance(extract_data(res), list)

    # 3. Theme
    res = client.get("/api/ux/theme?scene_type=erotic")
    assert res.status_code == 200
    assert extract_data(res)["theme_type"] == "erotic"

    # 4. What-If
    res = client.post("/api/ux/what-if", json={"choice_point": "敵との対峙"})
    assert res.status_code == 200
    assert "alternative_snippet" in extract_data(res)

    # 5. Pacing
    res = client.post("/api/ux/pacing", json={"chars_read": 500, "duration_ms": 2000, "scroll_speed_px_per_sec": 350})
    assert res.status_code == 200
    assert "suggested_metaphor_density" in extract_data(res)

    # 6. Monologue
    res = client.get("/api/ux/afterglow-monologue?character_name=メインヒロイン")
    assert res.status_code == 200
    assert "inner_monologue" in extract_data(res)

    # 7. Preference
    res = client.post("/api/ux/preference", json={"gap_type": "tsundere", "intensity": 70})
    assert res.status_code == 200

    # 9. Bedtime
    res = client.get("/api/ux/bedtime")
    assert res.status_code == 200
    assert "お疲れ様でした" in extract_data(res)["message"]


