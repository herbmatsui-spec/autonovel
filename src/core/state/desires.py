"""
src/core/state/desires.py — Desire to emotional hook mapping
"""

from src.models.emotional_hook import EmotionalHookSpec

DESIRE_TO_HOOK_MAP = {
    "カタルシス": "catharsis",
    "共感の最深": "empathy_peak",
    "背�筋の�寒さ": "chilling",
    "義�憤": "righteous_anger",
    " Triumph ": "triumph",
    "静�寂の喜び": "serenity",
    "�郷�愁": "nostalgia",
    "�畏敬": "awe",
}


def desires_to_hook(desires: list[str]) -> EmotionalHookSpec | None:
    """
    selected_desires の先頭を感情起点名に変�換し、EmotionalHookSpec を構�築する。

    desires が空なら None を返す。
    """
    if not desires:
        return None
    first = desires[0]
    hook_name = DESIRE_TO_HOOK_MAP.get(first)
    if hook_name is None:
        return None
    return EmotionalHookSpec(
        hook_name=hook_name,
        one_line_intent=first,
    )
