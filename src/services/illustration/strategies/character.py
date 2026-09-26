"""キャラクター立ち絵のプロンプト戦略。

`prompts.build_character_prompt` と同じ仕様。`book_context` のキーは
`name` / `character_name` の両方を許容する（旧実装との互換）。
"""

from __future__ import annotations

from src.models.illustration import IllustrationRequest, IllustrationType
from src.services.illustration.strategies.base import PromptStrategy


class CharacterStrategy(PromptStrategy):
    """立ち絵のプロンプトを作る。"""

    illustration_type = IllustrationType.CHARACTER

    def build_prompt(self, request: IllustrationRequest) -> str:
        override = request.prompt_override
        if override:
            return self._apply_safety(override, request.safety_level, IllustrationType.CHARACTER)

        name = self._ctx(request, "name", "character_name", default="character")
        role = self._ctx(request, "role", "character_role")
        appearance = self._ctx(request, "appearance", "character_description", "character_appearance")
        traits = self._ctx(request, "traits", "character_traits")
        background = self._ctx(request, "background", "setting")
        genre = self._ctx(request, "genre")

        parts = [
            "Full body character illustration, standing pose, clear visibility, masterpiece.",
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
        if genre:
            parts.append(self._genre_style(genre))
        parts.append("Clean line art, vivid colors, no text or letters in image.")

        prompt = " ".join(parts)
        return self._apply_safety(prompt, request.safety_level, IllustrationType.CHARACTER)


__all__ = ["CharacterStrategy"]
