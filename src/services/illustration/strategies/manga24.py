"""24コマ漫画シート（4列×6行）のプロンプト戦略。

1話につき1枚（4x6 = 24コマ）の漫画シートを1回のAPI呼び出しで生成する。
カメラ指示は**実際のグリッド座標**（row/col）に合わせて出力する。

- サイレント指定（`--no text, no speech bubbles, ...`）は必須。
- コマ数は 1..24 にクランプする。
- 24コマの要約分割は `plan_beats_24()` で行い、6個の繰り返しによる
  水増し（同じ要約の6回反復）は行わない。
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from src.models.illustration import IllustrationRequest, IllustrationType
from src.services.illustration.strategies.base import (
    PromptStrategy,
    distribute_paragraphs,
    split_paragraphs,
)

logger = logging.getLogger(__name__)

# グリッド構成
GRID_COLS = 4
GRID_ROWS = 6
TOTAL_PANELS = GRID_COLS * GRID_ROWS  # 24

# 1コマ要約の最大長（既存 build_yonkoma_prompt と同一のガード）
SUMMARY_MAX_CHARS = 220

# 24コマのビート定義（既存 `_YONKOMA_PANEL_BEATS` を4巡して拡張）
_BEATS = (
    ("setup", "wide establishing shot, introduce the situation and place"),
    ("develop", "medium shot, develop the conflict with a clear action"),
    ("turn", "close-up reaction shot, dramatic turning point or revelation"),
    ("climax", "dynamic action shot, emotional climax of the episode"),
    ("resolve", "medium shot, brief aftermath or quiet resolution"),
    ("aftertaste", "wide shot, lingering mood or hook for the next episode"),
)

# カメラ指示（4列×6行の実際の座標で定義）
_CAMERAS: Tuple[str, ...] = (
    "wide establishing shot, clear background, calm mood",
    "medium shot, character action, eye-level angle",
    "close-up reaction, expressive face, dramatic light",
    "medium close-up, dialogue between characters",
    "wide shot, location transition or time shift",
    "medium shot, new conflict emerging",
    "close-up, realization or emotional turn",
    "dynamic low-angle, action or impact moment",
    "wide two-shot, characters facing each other",
    "medium shot, rising tension in the setting",
    "close-up, decisive focus before action",
    "wide shot, transition toward the major event",
    "close-up, pivotal realization",
    "dynamic action shot, major confrontation",
    "extreme close-up, peak emotion at the climax",
    "wide shot, immediate aftermath of the climax",
    "medium shot, characters processing what happened",
    "wide shot, temporary resolution and calm",
    "quiet medium shot, character reflection",
    "close-up, lingering emotion and resolve",
    "wide shot, atmosphere of the setting",
    "medium shot, hint of the coming conflict",
    "medium shot, unresolved tension",
    "wide establishing shot, hook for the next episode",
)

# 24コマのプレースホルダ（シーン要約が無い場合）
# 起承転結＋余韻の7語を24コマ分へ巡回させる（UI が空でもエラーにしないため）。
_BASE_PLACEHOLDERS: Tuple[str, ...] = (
    "(導入)", "(展開)", "(転換)", "(危機)", "(決断)", "(衝突)", "(余韻)",
)


def _build_placeholders(count: int) -> Tuple[str, ...]:
    """ベース語を `count` 個まで巡回させたプレースホルダを作る。"""
    return tuple(
        _BASE_PLACEHOLDERS[i % len(_BASE_PLACEHOLDERS)] for i in range(count)
    )


_PLACEHOLDERS: Tuple[str, ...] = _build_placeholders(TOTAL_PANELS)


def panel_label(index: int) -> str:
    """0始まりのコマ番号を `row{r}-col{c}` 形式で返す。"""
    col = index % GRID_COLS
    row = index // GRID_COLS
    return f"row{row + 1}-col{col + 1}"


class Manga24Strategy(PromptStrategy):
    """24コマ漫画シートのプロンプトを作る。"""

    illustration_type = IllustrationType.MANGA_24PANEL

    @staticmethod
    def clamp_panels(panels: Optional[int]) -> int:
        """コマ数を 1..24 に収める。"""
        if panels is None:
            return TOTAL_PANELS
        try:
            value = int(panels)
        except (TypeError, ValueError):
            return TOTAL_PANELS
        return max(1, min(value, TOTAL_PANELS))

    def plan_beats_24(self, text: str, panels: int = TOTAL_PANELS) -> List[str]:
        """本文を `panels` 個のコマ要約へ分割する（LLM なしでも動く）。"""
        paragraphs = split_paragraphs(text, min_length=8)
        if not paragraphs:
            out = list(_PLACEHOLDERS[:panels])
            while len(out) < panels:
                out.append(_PLACEHOLDERS[-1])
            return out
        return distribute_paragraphs(paragraphs, panels)

    def build_prompt(self, request: IllustrationRequest) -> str:
        override = request.prompt_override
        if override:
            return self._apply_yonkoma_safety(override, request.safety_level)

        panels = self.clamp_panels(getattr(request, "panels", TOTAL_PANELS))
        episode_number = request.episode_number or 1
        title = self._ctx(request, "title", default="Untitled")
        genre = self._ctx(request, "genre")
        style = self._genre_style(genre)
        characters = self._ctx(request, "characters", "character_name", default="characters")
        synopsis = self._ctx(request, "synopsis")
        scene_text = (request.scene_text or "").strip()

        summaries = self.plan_beats_24(scene_text or synopsis, panels)

        parts: List[str] = [
            "Masterpiece manga sheet, full comic page, sequential manga story.",
            f"{TOTAL_PANELS} panels in a clean and organized "
            f"{GRID_COLS}x{GRID_ROWS} grid layout, even gutters, "
            "right-to-left reading order.",
            f"Telling the story of Episode {episode_number}: '{title}'.",
            f"Starring {characters}.",
            f"Narrative progression: {synopsis or (scene_text[:200] if scene_text else 'the episode as written')}",
            f"{style} Japanese manga art style, sharp lineart, screentone shading, "
            "high contrast black and white.",
            "--no text, no speech bubbles, no captions, no numbers, no words, "
            "no letters, no signature",
        ]

        for i in range(panels):
            beat, beat_desc = _BEATS[i % len(_BEATS)]
            camera = _CAMERAS[i % len(_CAMERAS)]
            summary = (summaries[i] if i < len(summaries) else "").strip()
            if len(summary) > SUMMARY_MAX_CHARS:
                summary = summary[:SUMMARY_MAX_CHARS] + "..."
            if not summary:
                summary = "(implicit progression based on previous panel)"
            parts.append(
                f"Panel {i + 1} ({panel_label(i)}) [{beat.upper()}] {camera}. "
                f"Beat: {beat_desc}. Scene: {summary}."
            )

        prompt = ", ".join(parts)
        return self._apply_yonkoma_safety(prompt, request.safety_level)

    def build_negative_prompt(self, request: IllustrationRequest) -> str:
        base = super().build_negative_prompt(request)
        return f"{base}, wrong panel count, western comic style, colored panels"


__all__ = [
    "GRID_COLS",
    "GRID_ROWS",
    "TOTAL_PANELS",
    "Manga24Strategy",
    "panel_label",
]
