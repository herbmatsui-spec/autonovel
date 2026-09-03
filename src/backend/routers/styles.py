"""Styles REST API Router
文体（Style DNA / 作家性プロファイル）の取得・蒸留（Distill）・音律整形（Reformat）エンドポイント。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.models.style_profile import StyleProfile
from src.presets.loader import SUPPORTED_GENRES, load_preset
from src.services.cadence_reformatter import CadenceStats, cadence_reformatter
from src.services.style_distiller import style_distiller_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/styles", tags=["styles"])

STYLES_JSON_PATH = Path(__file__).parent.parent.parent / "config" / "data" / "styles.json"


class DistillRequest(BaseModel):
    """文体蒸留リクエスト"""
    sample_text: str = Field(..., min_length=10, description="お手本となる小説サンプルテキスト")
    name_hint: str | None = Field(default=None, description="スタイル名のヒント")


class DistillResponse(BaseModel):
    """文体蒸留レスポンス"""
    success: bool = True
    profile: StyleProfile


class ReformatRequest(BaseModel):
    """音律・リズム整形リクエスト"""
    text: str = Field(..., description="整形対象の小説本文")


class ReformatResponse(BaseModel):
    """音律・リズム整形レスポンス"""
    reformatted_text: str
    stats: CadenceStats


class StylePresetSummary(BaseModel):
    """文体プリセット概要"""
    id: str
    name: str
    genre: str
    description: str
    tone: str
    profile: StyleProfile | None = None


class StyleEntry(BaseModel):
    """スタイル定義エントリ"""
    id: str
    name: str
    category: str
    instruction: str
    dialogue_ratio: str
    syntax_rhythm: str
    metaphor_dna: str
    noise_dna: str
    is_light: bool


class StyleCategory(BaseModel):
    """カテゴリ情報"""
    id: str
    label: str
    style_ids: list[str]


def _load_styles_json() -> dict[str, Any]:
    """styles.jsonをロード"""
    try:
        with open(STYLES_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load styles.json: {e}")
        return {}


@router.get("/all", response_model=list[StyleEntry])
async def get_all_styles() -> list[StyleEntry]:
    """全スタイル定義を取得（config/data/styles.jsonより）"""
    data = _load_styles_json()
    definitions = data.get("STYLE_DEFINITIONS", {})
    entries = []
    for style_id, style_def in definitions.items():
        entries.append(StyleEntry(
            id=style_id,
            name=style_def.get("name", ""),
            category=style_def.get("category", ""),
            instruction=style_def.get("instruction", ""),
            dialogue_ratio=style_def.get("dialogue_ratio", ""),
            syntax_rhythm=style_def.get("syntax_rhythm", ""),
            metaphor_dna=style_def.get("metaphor_dna", ""),
            noise_dna=style_def.get("noise_dna", ""),
            is_light=style_def.get("is_light", True)
        ))
    return entries


@router.get("/categories", response_model=list[StyleCategory])
async def get_style_categories() -> list[StyleCategory]:
    """スタイルカテゴリ一覧を取得"""
    data = _load_styles_json()
    definitions = data.get("STYLE_DEFINITIONS", {})
    categories: dict[str, list[str]] = {}
    for style_id, style_def in definitions.items():
        cat = style_def.get("category", "")
        if cat:
            categories.setdefault(cat, []).append(style_id)
    category_labels = {
        "tempo": "テンポ・爽快",
        "heavy": "重厚・シリアス",
        "dark": "暗黒・心理",
        "elegant": "優美・日常・職人"
    }
    result = []
    for cat_id, style_ids in categories.items():
        result.append(StyleCategory(
            id=cat_id,
            label=category_labels.get(cat_id, cat_id),
            style_ids=style_ids
        ))
    return result


@router.get("/{style_id}/preview", response_model=StyleEntry)
async def get_style_preview(style_id: str) -> StyleEntry:
    """特定スタイルのプレビュー情報を取得"""
    data = _load_styles_json()
    definitions = data.get("STYLE_DEFINITIONS", {})
    style_def = definitions.get(style_id)
    if not style_def:
        raise HTTPException(status_code=404, detail=f"Style not found: {style_id}")
    return StyleEntry(
        id=style_id,
        name=style_def.get("name", ""),
        category=style_def.get("category", ""),
        instruction=style_def.get("instruction", ""),
        dialogue_ratio=style_def.get("dialogue_ratio", ""),
        syntax_rhythm=style_def.get("syntax_rhythm", ""),
        metaphor_dna=style_def.get("metaphor_dna", ""),
        noise_dna=style_def.get("noise_dna", ""),
        is_light=style_def.get("is_light", True)
    )


# 代表的な日本語表示名マッピング
GENRE_DISPLAY_NAMES: dict[str, dict[str, str]] = {
    "zarma": {
        "name": "疾走・ざまぁ無双調",
        "description": "テンポの良い短文と体言止め、圧倒的実力差とカタルシスを強調する語り口",
        "tone": "クール・客観的 ＋ 勝利時の爆発的カタルシス",
    },
    "aku_reijo": {
        "name": "華麗・悪役令嬢調",
        "description": "優雅な語彙と内に秘めた知略・皮肉のギャップが際立つ一人称/三人称",
        "tone": "気品・優雅 ＋ 痛快な論破",
    },
    "cheat_tensei": {
        "name": "王道・チート転生調",
        "description": "明るい冒険感と爽快な能力無双、テンポの良い仲間との掛け合い",
        "tone": "ポジティブ・痛快・躍動感",
    },
    "slow_life": {
        "name": "情緒・スローライフ調",
        "description": "五感描写（味覚・触覚・温もり）と穏やかな時間の流れを味わう流麗な文体",
        "tone": "温厚・安らぎ・情緒的",
    },
    "dungeon_admin": {
        "name": "戦略・ダンジョン運営調",
        "description": "ステータス・数値管理と知略の駆け引きを楽しむ理知的で引きの強い文体",
        "tone": "理知的・計算高い・ワクワク感",
    },
    "modern_cheat": {
        "name": "現代ダンジョン・無双調",
        "description": "日常と非日常のコントラスト、掲示板・配信・SNS反応の臨場感あふれる文体",
        "tone": "現代的・軽快・ネットスラング対応",
    },
    "vrmmo": {
        "name": "VRMMO・ゲーマー調",
        "description": "ゲームシステムとプレイヤー心理を緻密に描く疾走感のある文体",
        "tone": "ゲーマー視点・知略・爽快",
    },
    "ts_tensei": {
        "name": "TS転生・アイデンティティ調",
        "description": "身体感覚と心理の揺らぎ、細やかな内面描写が光る文体",
        "tone": "繊細・内面独白多め",
    },
    "loop": {
        "name": "緊迫・死に戻りループ調",
        "description": "狂気と絶望、そして一縷の希望を掴み取る鋭い心理描写と疾走感",
        "tone": "シリアス・緊迫感・サスペンス",
    },
}


@router.get("/presets", response_model=list[StylePresetSummary])
async def get_style_presets() -> list[StylePresetSummary]:
    """利用可能な文体プリセット一覧を取得"""
    presets: list[StylePresetSummary] = []

    for genre in SUPPORTED_GENRES:
        meta = GENRE_DISPLAY_NAMES.get(
            genre,
            {"name": f"{genre}標準調", "description": "ジャンル標準文体", "tone": "標準的トーン"},
        )
        try:
            preset_dict = load_preset(genre)
            style_data = preset_dict.get("style", {})
            profile: StyleProfile | None = None
            if isinstance(style_data, dict) and style_data:
                profile = StyleProfile(
                    id=genre,
                    name=meta["name"],
                    genre_hint=genre,
                    tone_description=meta["tone"],
                    **{k: v for k, v in style_data.items() if k in StyleProfile.model_fields},
                )
            else:
                profile = StyleProfile(
                    id=genre,
                    name=meta["name"],
                    genre_hint=genre,
                    tone_description=meta["tone"],
                )
        except Exception as e:
            logger.debug(f"Failed to parse preset profile for {genre}: {e}")
            profile = StyleProfile(id=genre, name=meta["name"], genre_hint=genre)

        presets.append(
            StylePresetSummary(
                id=genre,
                name=meta["name"],
                genre=genre,
                description=meta["description"],
                tone=meta["tone"],
                profile=profile,
            )
        )

    return presets


@router.post("/distill", response_model=DistillResponse)
async def distill_style(request: DistillRequest) -> DistillResponse:
    """提供されたサンプル文章から作家性DNA（StyleProfile）を自動抽出"""
    try:
        profile = await style_distiller_service.distill_from_text(
            sample_text=request.sample_text,
            name_hint=request.name_hint,
        )
        return DistillResponse(success=True, profile=profile)
    except Exception as e:
        logger.error(f"Style distillation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文体抽出エラー: {str(e)}")


@router.post("/reformat", response_model=ReformatResponse)
async def reformat_cadence(request: ReformatRequest) -> ReformatResponse:
    """本文の文末重複（〜た）を補正し、自然な音律とリズムへ整形"""
    try:
        reformatted, stats = cadence_reformatter.reformat_novel_text(request.text)
        return ReformatResponse(reformatted_text=reformatted, stats=stats)
    except Exception as e:
        logger.error(f"Cadence reformat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"リズム整形エラー: {str(e)}")