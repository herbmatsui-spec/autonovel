"""表紙・挿絵・キャラクターの画像生成用プロンプト構築ユーティリティ。

各関数は小さく、低性能なLLMでも1つずつ実装・テストできるよう分割している。
"""

from typing import Dict, List

from src.models.illustration import IllustrationType, SafetyLevel

# ジャンルごとの視覚スタイルのヒント
_GENRE_STYLE_HINTS: Dict[str, str] = {
    "ファンタジー": "epic fantasy art style, magical atmosphere, detailed armor and castles",
    "ラブコメ": "soft pastel shoujo style, romantic tone, warm lighting",
    "SF": "futuristic sci-fi style, neon lighting, sleek technology",
    "ホラー": "dark gothic horror style, eerie shadows, high contrast",
    "ミステリー": "noir mystery style, muted colors, suspenseful mood",
    "歴史": "historical painterly style, period accurate clothing",
    "ライトノベル": "modern light novel cover style, vibrant colors, dynamic composition",
}

# 表紙のバリエーション別カメラワーク指示
_COVER_VARIATIONS: List[str] = [
    "centered composition, hero framing, title space at top",
    "wide cinematic shot, dramatic perspective, title space at bottom",
    "close-up portrait focus, soft bokeh background, title space on side",
]


def _genre_hint(genre: str) -> str:
    if not genre:
        return "modern light novel cover style, vibrant colors"
    for key, hint in _GENRE_STYLE_HINTS.items():
        if key in genre:
            return hint
    return f"{genre} themed illustration style, professional book cover"


def build_cover_prompt(book_context: Dict[str, str], variation: int = 0) -> str:
    """表紙生成プロンプトを構築する。

    book_context には title / genre / concept / keywords を含める想定。
    """
    title = book_context.get("title", "Untitled")
    genre = book_context.get("genre", "")
    concept = book_context.get("concept", "")
    keywords = book_context.get("keywords", "")

    style = _genre_hint(genre)
    cam = _COVER_VARIATIONS[variation % len(_COVER_VARIATIONS)]

    parts = [
        "Professional novel book cover illustration.",
        f"Title theme: {title}.",
        style,
        cam,
    ]
    if concept:
        parts.append(f"Story concept: {concept}")
    if keywords:
        parts.append(f"Visual motifs: {keywords}")
    parts.append("High quality, detailed, print-ready, no text or letters in image.")
    return " ".join(parts)


def build_scene_prompt(scene_text: str, book_context: Dict[str, str]) -> str:
    """挿絵（シーン）生成プロンプトを構築する。"""
    genre = book_context.get("genre", "")
    style = _genre_hint(genre)

    scene = scene_text.strip()
    if len(scene) > 400:
        scene = scene[:400] + "..."

    parts = [
        "Detailed illustrative scene from a novel.",
        style,
        f"Scene description: {scene}",
        "Cinematic lighting, rich detail, no text or letters in image.",
    ]
    return " ".join(parts)


def build_character_prompt(character_data: Dict[str, str]) -> str:
    """キャラクター立ち絵生成プロンプトを構築する。"""
    name = character_data.get("name", "character")
    role = character_data.get("role", "")
    appearance = character_data.get("appearance", "")
    traits = character_data.get("traits", "")
    background = character_data.get("background", "")

    parts = [
        "Full body character illustration, standing pose, clear visibility.",
        f"Character name: {name}.",
    ]
    if role:
        parts.append(f"Role: {role}.")
    if appearance:
        parts.append(f"Appearance: {appearance}.")
    else:
        parts.append("Detailed original character design.")
    if traits:
        parts.append(f"Personality reflected in expression: {traits}.")
    if background:
        parts.append(f"Setting hint: {background}.")
    parts.append("Clean line art, vivid colors, no text or letters in image.")
    return " ".join(parts)


def apply_safety_modifier(
    prompt: str, safety_level: SafetyLevel, illo_type: IllustrationType
) -> str:
    """R15等の安全レベルに応じたプロンプト修飾を付与する。

    safety_level は src / autonovel.src いずれの経路で作られた enum でも
    比較できるよう、値(.value)で判定する。
    """
    try:
        is_r15 = safety_level.value == SafetyLevel.R15_CONTENT.value
    except AttributeError:
        is_r15 = str(getattr(safety_level, "value", safety_level)) == "R15_CONTENT"
    if not is_r15:
        return prompt

    if illo_type == IllustrationType.CHARACTER:
        return (
            prompt + " Tasteful R15 artistic representation, romantic atmosphere, "
            "elegant and non-explicit."
        )
    return (
        prompt
        + " Tasteful R15 artistic representation, intimate but not explicit, artistic lighting."
    )
