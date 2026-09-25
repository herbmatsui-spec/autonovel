"""Prompt generator for 24-panel manga sheet (NanoBanana 2 Lite / Gemini 3.1 Flash-Lite Image)."""
from __future__ import annotations

from typing import List, Optional
from src.services.manga.models import CharacterReference, MangaEpisodeInput


class MangaPromptGenerator:
    """1話につき1枚の24コマ漫画シートを生成するためのプロンプトビルダー。"""

    DEFAULT_NEGATIVE_PROMPT = (
        "text, speech bubbles, letters, watermark, signature, deformed panels, "
        "irregular messy grid, blurry, low resolution, 3d render, photograph, "
        "color bleeding, distorted faces"
    )

    def __init__(self, default_negative_prompt: Optional[str] = None):
        self.negative_prompt = (
            default_negative_prompt
            if default_negative_prompt is not None
            else self.DEFAULT_NEGATIVE_PROMPT
        )

    def build_prompt(
        self,
        episode: MangaEpisodeInput,
        character_refs: Optional[List[CharacterReference]] = None,
    ) -> str:
        """1話1枚（24コマ一括）マンガシート生成用のメインプロンプトを構築する。"""
        char_names = ", ".join(episode.characters) if episode.characters else "characters"
        setting_clause = f"in {episode.setting}, " if episode.setting else ""

        # 参照画像がある場合のアノテーション
        ref_notes = ""
        if character_refs:
            ref_names = ", ".join([c.name for c in character_refs])
            ref_notes = f"maintaining strictly consistent character appearance with {ref_names}, "

        prompt_parts = [
            "masterpiece manga sheet, full comic page, sequential manga story",
            f"24 panels in a clean and organized 4x6 grid layout",
            f"telling the story of Episode {episode.episode_number}: '{episode.title}'",
            f"{setting_clause}starring {char_names}",
            f"narrative progression: {episode.synopsis}",
            f"{ref_notes}japanese manga art style, sharp lineart, screentone shading, high contrast black and white",
            "--no text, no speech bubbles, no captions, no numbers, no words"
        ]

        return ", ".join(prompt_parts)

    def build_negative_prompt(self, additional_negatives: Optional[str] = None) -> str:
        """ネガティブプロンプトを構築する。"""
        if additional_negatives:
            return f"{self.negative_prompt}, {additional_negatives}"
        return self.negative_prompt
