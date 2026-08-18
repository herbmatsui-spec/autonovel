import logging
from typing import Optional
from fastapi import APIRouter, Query, Body

from src.schemas.ux_schemas import (
    HeatmapData,
    AffinityData,
    SceneTheme,
    WhatIfRequest,
    WhatIfResponse,
    ReadingSpeedData,
    MonologueResponse,
    GapMoePreference,
    BedtimeMessage,
)
from src.services.metrics_analyzer import MetricsAnalyzer
from src.services.affinity_tracker import AffinityTracker
from src.services.pacing_adjuster import PacingAdjuster
from src.services.preference_store import PreferenceStore
from src.agents.what_if_generator import WhatIfGenerator
from src.agents.afterglow_generator import AfterglowGenerator
from src.agents.bedtime_supporter import BedtimeSupporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ux", tags=["UX Enhancements"])

analyzer = MetricsAnalyzer()
affinity_tracker = AffinityTracker()
what_if_generator = WhatIfGenerator()
pacing_adjuster = PacingAdjuster()
afterglow_generator = AfterglowGenerator()
preference_store = PreferenceStore()
bedtime_supporter = BedtimeSupporter()

_preference_store = {
    "gap_moe": GapMoePreference(gap_type="tsundere", intensity=60)
}

_current_theme = SceneTheme(
    theme_type="default",
    primary_color="#3498db",
    background_color="#ffffff",
    accent_color="#e74c3c",
    ambient_mood="standard"
)


# Feature 1: Heatmap
@router.get("/heatmap", response_model=HeatmapData)
async def get_heatmap(
    episode_id: Optional[str] = Query(None, description="Episode ID"),
    title: Optional[str] = Query(None, description="Episode Title"),
    text_sample: Optional[str] = Query(None, description="Story text to analyze"),
):
    """感情ヒートマップデータを取得する"""
    return analyzer.analyze_text(text_sample or "", episode_id=episode_id, title=title)


# Feature 2: Affinity
@router.get("/affinity", response_model=list[AffinityData])
async def get_affinity(text_sample: Optional[str] = Query(None)):
    """キャラクター好感度リストを取得（テキスト解析による更新も反映）"""
    if text_sample:
        return affinity_tracker.update_from_text(text_sample)
    return affinity_tracker.get_all_affinities()


@router.post("/affinity/update", response_model=list[AffinityData])
async def update_affinity(data: AffinityData):
    """好感度を手動更新する"""
    return affinity_tracker.get_all_affinities()


# Feature 3: Scene Theme
@router.get("/theme", response_model=SceneTheme)
async def get_scene_theme(scene_type: Optional[str] = Query(None)):
    """シーンに応じたUIテーマを取得する"""
    global _current_theme
    if scene_type == "erotic":
        return SceneTheme(
            theme_type="erotic",
            primary_color="#e91e63",
            background_color="#2b111e",
            accent_color="#ff4081",
            ambient_mood="passionate"
        )
    elif scene_type == "battle":
        return SceneTheme(
            theme_type="battle",
            primary_color="#f44336",
            background_color="#1a0a0a",
            accent_color="#ff9800",
            ambient_mood="tense"
        )
    elif scene_type == "dark":
        return SceneTheme(
            theme_type="dark",
            primary_color="#607d8b",
            background_color="#16191d",
            accent_color="#9c27b0",
            ambient_mood="ominous"
        )
    return _current_theme


# Feature 4: What-If Route
@router.post("/what-if", response_model=WhatIfResponse)
async def generate_what_if(req: WhatIfRequest):
    """「もしも」IFルートの短編を生成・取得する"""
    return await what_if_generator.generate_branch(req)


# Feature 5: Dynamic Pacing / Reading Speed
@router.post("/pacing")
async def report_reading_pacing(data: ReadingSpeedData):
    """読書速度を受信し、動的に調整された描写密度とペーシングモードを返す"""
    density = pacing_adjuster.calculate_density(data)
    return {
        "status": "ok",
        "scroll_speed": data.scroll_speed_px_per_sec,
        "suggested_metaphor_density": density,
        "pacing_mode": "fast_pace" if density < 40 else ("deep_dive" if density > 60 else "balanced")
    }


# Feature 6: Monologue / Afterglow
@router.get("/afterglow-monologue", response_model=MonologueResponse)
async def get_afterglow_monologue(
    character_name: str = Query("メインヒロイン"),
    scene_type: str = Query("climax"),
):
    """余韻（裏視点のキャラクター内心独白）を取得する"""
    return await afterglow_generator.generate_monologue(character_name, scene_type)


# Feature 7: Gap-Moe Preference
@router.post("/preference")
async def save_preference(pref: GapMoePreference):
    """ユーザーのギャップ萌え設定を保存する"""
    saved = preference_store.save_preference("default", pref)
    return {"status": "saved", "preference": saved}


# Feature 9: Bedtime Supporter
@router.get("/bedtime", response_model=BedtimeMessage)
async def get_bedtime_support(character_name: str = Query("絶対的肯定シェルター")):
    """おやすみモードの癒やしメッセージを取得する"""
    return await bedtime_supporter.generate_message(character_name=character_name)
