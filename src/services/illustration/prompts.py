"""表紙・挿絵・キャラクターの画像生成用プロンプト構築ユーティリティ。

各関数は小さく、低性能なLLMでも1つずつ実装・テストできるよう分割している。
"""

from src.models.illustration import IllustrationType, SafetyLevel

# ジャンルごとの視覚スタイルのヒント
_GENRE_STYLE_HINTS: dict[str, str] = {
    "ファンタジー": "epic fantasy art style, magical atmosphere, detailed armor and castles",
    "ラブコメ": "soft pastel shoujo style, romantic tone, warm lighting",
    "SF": "futuristic sci-fi style, neon lighting, sleek technology",
    "ホラー": "dark gothic horror style, eerie shadows, high contrast",
    "ミステリー": "noir mystery style, muted colors, suspenseful mood",
    "歴史": "historical painterly style, period accurate clothing",
    "ライトノベル": "modern light novel cover style, vibrant colors, dynamic composition",
}

# 表紙のバリエーション別カメラワーク指示
_COVER_VARIATIONS: list[str] = [
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


def build_cover_prompt(book_context: dict[str, str], variation: int = 0) -> str:
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


def build_scene_prompt(scene_text: str, book_context: dict[str, str]) -> str:
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


def build_character_prompt(character_data: dict[str, str]) -> str:
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


# ---- 4コマ風/6コマ要約漫画用のプロンプト -----------------------------
# 6コマに固定 (起/承/転/結 + 余韻2コマ) することで、話の流れが一目で分かる構成にする。

_YONKOMA_PANEL_BEATS: list[tuple[str, str]] = [
    ("setup", "wide establishing shot, introduce the situation and place"),
    ("develop", "medium shot, develop the conflict with a clear action"),
    ("turn", "close-up reaction shot, dramatic turning point or revelation"),
    ("climax", "dynamic action shot, emotional climax of the episode"),
    ("resolve", "medium shot, brief aftermath or quiet resolution"),
    ("aftertaste", "wide shot, lingering mood or hook for the next episode"),
]


def _yonkoma_camera_directives() -> list[str]:
    """6コマ分のカメラ指示 (上段3コマ・下段3コマ) を返す。"""
    return [
        "Panel 1 (top-left): wide establishing shot, clear background, calm mood",
        "Panel 2 (top-center): medium shot, character action, eye-level angle",
        "Panel 3 (top-right): close-up reaction, expressive face, dramatic light",
        "Panel 4 (bottom-left): dynamic low-angle, action or impact moment",
        "Panel 5 (bottom-center): medium shot, aftermath, softer lighting",
        "Panel 6 (bottom-right): wide or extreme wide shot, lingering atmosphere, hook for next",
    ]


def build_yonkoma_prompt(
    episode_summaries: list[str],
    book_context: dict[str, str],
    panels: int = 6,
) -> str:
    """1話分の流れを N コマ漫画として可視化するプロンプトを構築する。

    Args:
        episode_summaries: 各コマに割り当てる短いシーン要約。
                           長さは ``panels`` に揃うよう呼び出し側で調整する想定。
        book_context: ``title`` / ``genre`` / ``character_name`` / ``character_description`` を含む dict。
        panels: コマ数。3〜6 を許容 (6以外では簡略化されたコマ割りを出力)。

    Returns:
        Imagen に渡す英語プロンプト文字列。
    """
    panels = max(3, min(int(panels or 6), 6))
    beats = _YONKOMA_PANEL_BEATS[:panels]
    camera = _yonkoma_camera_directives()[:panels]

    title = book_context.get("title", "Untitled")
    genre = book_context.get("genre", "")
    style = _genre_hint(genre)

    # サマリ長を整える (過長プロンプト防止)
    normalized: list[str] = []
    for i in range(panels):
        summary = episode_summaries[i] if i < len(episode_summaries) else ""
        summary = (summary or "").strip()
        if len(summary) > 220:
            summary = summary[:220] + "..."
        normalized.append(summary)

    parts: list[str] = [
        "Six-panel (or N-panel) storyboard illustration summarizing one episode.",
        f"Work title: {title}.",
        style,
        "Manga / comic style, clean line art, panel grid layout (top row 3 panels, bottom row 3 panels).",
        "Each panel must show a distinct beat of the story so the episode flow is readable at a glance.",
        "Use speech bubbles sparingly only when essential; prefer visual storytelling.",
        "Cinematic lighting, expressive faces, dynamic camera angles per panel.",
        "No text or letters in image (titles, captions, sound effects are not rendered).",
    ]

    for i, (beat, beat_desc) in enumerate(beats):
        cam = camera[i] if i < len(camera) else "medium shot"
        summary = normalized[i] or "(implicit progression based on previous panel)"
        parts.append(f"Panel {i + 1} [{beat.upper()}] {cam}. Beat: {beat_desc}. Scene: {summary}.")

    return " ".join(parts)


def apply_yonkoma_safety_modifier(prompt: str, safety_level: SafetyLevel) -> str:
    """4コマ風プロンプト用の R15 修飾。``apply_safety_modifier`` と同じ調子を保つ。"""
    try:
        is_r15 = safety_level.value == SafetyLevel.R15_CONTENT.value
    except AttributeError:
        is_r15 = str(getattr(safety_level, "value", safety_level)) == "R15_CONTENT"
    if not is_r15:
        return prompt
    return (
        prompt + " Tasteful R15 artistic representation, romantic atmosphere, "
        "elegant and non-explicit in all panels."
    )
