# src/agents/enrichment/multimedia.py
"""マルチメディアシナリオ生成モジュール"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from pathlib import Path

try:
    from jinja2 import Environment, FileSystemLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False


# テンプレート環境
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "prompts" / "enrichment" / "templates"
if JINJA2_AVAILABLE and TEMPLATE_DIR.exists():
    _jinja_env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
    )
else:
    _jinja_env = None


@dataclass
class SceneSegment:
    """検出されたシーンセグメント"""
    scene_type: str
    start: int
    end: int
    text: str
    characters: list[str]
    tension_level: int


def classify_scene_type(text: str, writing_context: dict) -> list[SceneSegment]:
    """シーンタイプ分類（Step 31）"""
    segments = []
    
    # 簡易実装: キーワードベース分類
    # 本文全体を1シーンとして扱う（将来的には文/段落レベルで分割）
    
    # キャラクター抽出
    characters = writing_context.get("characters", [])
    if isinstance(characters, str):
        characters = [characters]
    
    # 緊張度推定
    tension_keywords_high = ["戦", "戦い", "バトル", "死", "殺", "敵", "剣", "魔法", "攻撃", "防御", "必死", "命懸け"]
    tension_keywords_medium = ["緊張", "不安", "焦り", "追跡", "逃走", "対峙", "決断", "選択"]
    tension_keywords_low = ["会話", "日常", "食事", "休憩", "移動", "説明", "回想"]
    
    text_lower = text.lower()
    tension = 5  # デフォルト
    if any(kw in text_lower for kw in tension_keywords_high):
        tension = 8
    elif any(kw in text_lower for kw in tension_keywords_medium):
        tension = 6
    elif any(kw in text_lower for kw in tension_keywords_low):
        tension = 3
    
    # シーンタイプ判定
    scene_type = "daily_life"
    # 感情のピークを最優先（悲劇的結末など）
    if any(kw in text_lower for kw in ["別れ", "死", "涙", "悲劇", "喪失", "犠牲"]):
        scene_type = "emotional_peak"
    elif any(kw in text_lower for kw in ["クライマックス", "最終決戦", "ラストバトル", "決着"]):
        scene_type = "climax"
    elif any(kw in text_lower for kw in tension_keywords_high):
        scene_type = "battle"
    elif any(kw in text_lower for kw in ["告白", "キス", "抱擁", "恋", "愛", "プロポーズ"]):
        scene_type = "romance"
    elif any(kw in text_lower for kw in ["正体", "真実", "秘密", "判明", "発覚", "記憶", "過去"]):
        scene_type = "revelation"
    
    # トリガーシーンかどうか
    trigger_scenes = ["climax", "battle", "emotional_peak", "revelation", "romance"]
    is_trigger = scene_type in trigger_scenes
    
    if is_trigger:
        segments.append(SceneSegment(
            scene_type=scene_type,
            start=0,
            end=len(text),
            text=text[:2000],  # 最初の2000文字を使用
            characters=characters[:5],
            tension_level=tension,
        ))
    
    return segments


def render_manga_script(segment: SceneSegment, text: str) -> dict:
    """マンガ台本レンダリング"""
    # 簡易実装: テキストからコマ構成を推定
    sentences = re.split(r'(?<=[。！？])', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # 4-6コマ/ページ、2-3ページ想定
    panels_per_page = 5
    total_panels = min(len(sentences), 12)
    total_pages = max(1, (total_panels + panels_per_page - 1) // panels_per_page)
    
    pages = []
    panel_idx = 0
    for page_num in range(total_pages):
        page_panels = []
        for i in range(panels_per_page):
            if panel_idx >= total_panels:
                break
            sent = sentences[panel_idx] if panel_idx < len(sentences) else ""
            panel_idx += 1
            
            # 話者推定
            speaker = ""
            for char in segment.characters:
                if char in sent:
                    speaker = char
                    break
            
            page_panels.append({
                "panel_number": len(page_panels) + 1,
                "visual": f"コマ{len(page_panels)+1}: {sent[:50]}...",
                "dialogue": sent if speaker else "",
                "sfx": "" if not any(kw in sent for kw in ["ドーン", "バーン", "ザッ", "ガッ", "キーン"]) else "効果音",
                "camera": "ミディアムショット",
                "character_focus": speaker,
            })
        pages.append({"page_number": page_num + 1, "panels": page_panels})
    
    if _jinja_env:
        try:
            template = _jinja_env.get_template("manga_script.j2")
            return json.loads(template.render(
                scene_info={
                    "title": f"{segment.scene_type}シーン",
                    "scene_type": segment.scene_type,
                    "characters": segment.characters,
                    "tension_level": segment.tension_level,
                },
                pages=pages,
            ))
        except Exception:
            pass
    
    # フォールバック: 直接構築
    return {
        "format": "manga_script",
        "title": f"{segment.scene_type}シーン",
        "scene_type": segment.scene_type,
        "pages": pages,
        "metadata": {
            "estimated_pages": total_pages,
            "total_panels": total_panels,
            "key_characters": segment.characters,
            "tension_level": segment.tension_level,
        },
    }


def render_radio_drama(segment: SceneSegment, text: str) -> dict:
    """ラジオドラマ台本レンダリング"""
    sentences = re.split(r'(?<=[。！？])', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    cues = []
    for i, sent in enumerate(sentences[:10]):  # 最大10キュー
        # 話者推定
        speaker = "ナレーター"
        for char in segment.characters:
            if char in sent:
                speaker = char
                break
        
        is_narration = speaker == "ナレーター"
        
        cues.append({
            "cue_number": i + 1,
            "type": "narration" if is_narration else "dialogue",
            "sfx": "環境音" if i == 0 else "",
            "bgm": "シーン冒頭BGM" if i == 0 else ("クライマックスBGM" if i == len(sentences)-1 else ""),
            "narration": sent if is_narration else "",
            "dialogue": [] if is_narration else [{
                "character": speaker,
                "line": sent,
                "direction": "通常" if segment.tension_level < 6 else "緊迫"
            }],
            "duration_estimate_sec": max(5, len(sent) // 3),
        })
    
    if _jinja_env:
        try:
            template = _jinja_env.get_template("radio_drama.j2")
            return json.loads(template.render(
                scene_info={
                    "title": f"{segment.scene_type}シーン",
                    "scene_type": segment.scene_type,
                    "characters": segment.characters,
                    "tension_level": segment.tension_level,
                },
                cues=cues,
            ))
        except Exception:
            pass
    
    return {
        "format": "radio_drama",
        "title": f"{segment.scene_type}シーン",
        "scene_type": segment.scene_type,
        "cues": cues,
        "metadata": {
            "total_duration_sec": sum(c["duration_estimate_sec"] for c in cues),
            "key_characters": segment.characters,
            "tension_level": segment.tension_level,
            "cast_count": len(segment.characters),
        },
    }


def render_anime_storyboard(segment: SceneSegment, text: str) -> dict:
    """アニメ絵コンテレンダリング"""
    sentences = re.split(r'(?<=[。！？])', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    cuts = []
    for i, sent in enumerate(sentences[:15]):  # 最大15カット
        cuts.append({
            "cut_number": i + 1,
            "duration_sec": max(2, len(sent) // 5),
            "camera": "パン・左から右" if i % 3 == 0 else ("ズームイン" if i % 3 == 1 else "固定"),
            "action": sent[:80],
            "dialogue": "",
            "background": "シーン背景",
            "animation_note": "標準",
            "character_layout": "",
            "effect": "",
        })
    
    if _jinja_env:
        try:
            template = _jinja_env.get_template("anime_storyboard.j2")
            return json.loads(template.render(
                scene_info={
                    "title": f"{segment.scene_type}シーン",
                    "scene_type": segment.scene_type,
                    "characters": segment.characters,
                    "tension_level": segment.tension_level,
                },
                cuts=cuts,
            ))
        except Exception:
            pass
    
    return {
        "format": "anime_storyboard",
        "title": f"{segment.scene_type}シーン",
        "scene_type": segment.scene_type,
        "cuts": cuts,
        "metadata": {
            "total_duration_sec": sum(c["duration_sec"] for c in cuts),
            "total_cuts": len(cuts),
            "key_characters": segment.characters,
            "tension_level": segment.tension_level,
            "backgrounds": ["シーン背景"],
        },
    }


def render_live_action_shots(segment: SceneSegment, text: str) -> dict:
    """実写ショットリストレンダリング"""
    sentences = re.split(r'(?<=[。！？])', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    shots = []
    for i, sent in enumerate(sentences[:10]):
        shot_types = ["ミディアムショット", "クローズアップ", "ワイドショット", "オーバーショルダー", "エクストリームクローズアップ"]
        lenses = ["35mm", "50mm", "85mm", "24mm", "135mm"]
        movements = ["固定", "パン", "チルト", "ドリーイン", "ハンドヘルド"]
        
        shots.append({
            "shot_number": i + 1,
            "scene_slug": "INT. シーン - 昼/夜",
            "shot_type": shot_types[i % len(shot_types)],
            "lens": lenses[i % len(lenses)],
            "movement": movements[i % len(movements)],
            "actors": segment.characters[:3],
            "vfx": "なし",
            "dialogue": sent[:60] if any(c in sent for c in segment.characters) else "",
            "lighting": "自然光" if i % 2 == 0 else "ドラマティック照明",
            "duration_sec": max(3, len(sent) // 4),
            "notes": "",
        })
    
    if _jinja_env:
        try:
            template = _jinja_env.get_template("live_action_shots.j2")
            return json.loads(template.render(
                scene_info={
                    "title": f"{segment.scene_type}シーン",
                    "scene_type": segment.scene_type,
                    "characters": segment.characters,
                    "tension_level": segment.tension_level,
                },
                shots=shots,
            ))
        except Exception:
            pass
    
    return {
        "format": "live_action_shots",
        "title": f"{segment.scene_type}シーン",
        "scene_type": segment.scene_type,
        "shots": shots,
        "metadata": {
            "total_shots": len(shots),
            "total_duration_sec": sum(s["duration_sec"] for s in shots),
            "key_actors": segment.characters,
            "tension_level": segment.tension_level,
            "locations": ["INT. シーン - 昼/夜"],
        },
    }


def generate_scenarios(text: str, writing_context: dict, llm: Any = None) -> dict[str, dict]:
    """マルチメディアシナリオ生成（エントリーポイント・Step 36）"""
    # 1. シーン分類
    segments = classify_scene_type(text, writing_context)
    
    if not segments:
        return {}
    
    # 最初のトリガーシーンのみ処理（将来的には複数対応）
    segment = segments[0]
    
    # 2. 各フォーマットレンダリング
    results = {}
    
    # マンガ台本
    if _jinja_env or True:
        results["manga_script"] = render_manga_script(segment, text)
    
    # ラジオドラマ
    results["radio_drama"] = render_radio_drama(segment, text)
    
    # アニメ絵コンテ
    results["anime_storyboard"] = render_anime_storyboard(segment, text)
    
    # 実写ショットリスト
    results["live_action_shots"] = render_live_action_shots(segment, text)
    
    return results