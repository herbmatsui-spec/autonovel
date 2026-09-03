"""
プリセットローダー統合
FullAuto の STORY_ARCHETYPES と EasyMode の load_preset を統合
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def load_preset_for_pipeline(genre: str, archetype_key: str) -> dict[str, Any]:
    """
    パイプライン用プリセット読み込み
    - EasyMode のジャンル別プリセット (zarma, aku_reijo 等)
    - FullAuto のアーキタイプ設定 (STORY_ARCHETYPES)
    を合成して返す
    """
    # 1. EasyMode プリセット読み込み (ジャンル -> プリセット名マッピング)
    preset = _load_easy_mode_preset(genre)

    # 2. FullAuto アーキタイプ設定取得
    archetype_settings = _get_archetype_settings(archetype_key)

    # 3. 合成: アーキタイプ設定でプリセットを上書き/補完
    merged = _merge_preset_with_archetype(preset, archetype_settings)

    # 4. メタデータ追加
    merged["_meta"] = {
        "genre": genre,
        "archetype_key": archetype_key,
        "source": "merged",
    }

    return merged


def _load_easy_mode_preset(genre: str) -> dict[str, Any]:
    """EasyMode プリセット読み込み (ジャンル名 -> 内部プリセット名変換)"""
    # ジャンル名からプリセット名へのマッピング
    genre_to_preset = {
        "ファンタジー": "zarma",
        "恋愛": "aku_reijo",
        "SF": "cheat_tensei",
        "歴史": "slow_life",
        "現代": "modern_cheat",
        "官能/ロマンス": "pure_love_erotic",
        "異世界": "zarma",
        "追放ざまぁ": "zarma",
        "悪役令嬢": "aku_reijo",
        "チート転生": "cheat_tensei",
        "スローライフ": "slow_life",
        "ダンジョン運営": "dungeon_admin",
        "現代チート": "modern_cheat",
        "TS転生": "ts_tensei",
        "VRMMO": "vrmmo",
        "ループ": "loop",
    }

    preset_name = genre_to_preset.get(genre, "zarma")

    try:
        from src.presets.loader import load_preset as load_em_preset

        return load_em_preset(preset_name)
    except Exception as e:
        logger.warning(f"EasyMode preset load failed for {preset_name}: {e}")
        return {}


def _get_archetype_settings(archetype_key: str) -> dict[str, Any]:
    """FullAuto STORY_ARCHETYPES から設定取得"""
    try:
        from config import STORY_ARCHETYPES

        return STORY_ARCHETYPES.get(archetype_key, {})
    except Exception as e:
        logger.warning(f"STORY_ARCHETYPES load failed: {e}")
        return {}


def _merge_preset_with_archetype(
    preset: dict[str, Any], archetype: dict[str, Any]
) -> dict[str, Any]:
    """プリセットとアーキタイプ設定を合成 (アーキタイプ優先で上書き)"""
    import copy

    merged = copy.deepcopy(preset)

    # アーキタイプ設定をトップレベルにマージ (style_key, cheat_scale 等)
    for key in [
        "style_key",
        "cheat_scale",
        "growth_curve",
        "system_assist",
        "cost_severity",
        "reality_cost",
        "plot_pattern",
        "default_target_eps",
        "default_word_count",
    ]:
        if key in archetype:
            merged[key] = archetype[key]

    # tension 曲線があればマージ
    if "tension" in archetype:
        merged["tension"] = archetype["tension"]

    return merged


def get_style_key(preset: dict[str, Any], default: str = "style_web_standard") -> str:
    """プリセットから style_key を安全に取得"""
    return preset.get("style_key", default)


def get_cheat_scale(preset: dict[str, Any], default: int = 4) -> int:
    """プリセットから cheat_scale を安全に取得"""
    return preset.get("cheat_scale", default)


def get_growth_curve(preset: dict[str, Any], default: str = "最初からカンスト(無双)") -> str:
    """プリセットから growth_curve を安全に取得"""
    return preset.get("growth_curve", default)


def get_system_assist(preset: dict[str, Any], default: int = 70) -> int:
    """プリセットから system_assist を安全に取得"""
    return preset.get("system_assist", default)


def get_cost_severity(preset: dict[str, Any], default: int = 2) -> int:
    """プリセットから cost_severity を安全に取得"""
    return preset.get("cost_severity", default)


def get_tension_curve(preset: dict[str, Any]) -> dict[str, Any]:
    """プリセットから tension 曲線設定を取得 (EasyMode 互換)"""
    # EasyMode 形式: tension.curve_points, tension.catharsis_spikes
    # FullAuto 形式: 直接 curve_points 等
    tension = preset.get("tension", {})
    if not tension:
        # デフォルト曲線
        return {
            "curve_points": [[0.0, 0.3], [0.25, 0.6], [0.5, 0.8], [0.75, 0.9], [1.0, 1.0]],
            "catharsis_spikes": [0.25, 0.5, 0.75, 1.0],
        }

    # 既に EasyMode 形式ならそのまま
    if "curve_points" in tension:
        return tension

    # FullAuto 形式なら変換
    return {
        "curve_points": tension.get(
            "curve_points", [[0.0, 0.3], [0.25, 0.6], [0.5, 0.8], [0.75, 0.9], [1.0, 1.0]]
        ),
        "catharsis_spikes": tension.get("catharsis_spikes", [0.25, 0.5, 0.75, 1.0]),
    }


def get_plot_pattern(preset: dict[str, Any], default: str = "exile_rise") -> str:
    """プリセットから plot_pattern を取得"""
    return preset.get("plot_pattern", default)
