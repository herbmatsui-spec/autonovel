"""挿絵（単発シーン）のプロンプト戦略。

`prompts.build_scene_prompt` と同じ仕様（シーン文は 400 文字で打ち切り）。
`scene_text` が無い場合は `book_context` から汎用プロンプトを組み立てる
（旧 `IllustrationAgent._generate_episode` / `_build_episode_prompt` の
挙動を吸収）。
"""

from __future__ import annotations

from src.models.illustration import IllustrationRequest, IllustrationType
from src.services.illustration.strategies.base import PromptStrategy

# シーン説明の最大長（既存仕様と同一）
SCENE_MAX_CHARS = 400


class EpisodeStrategy(PromptStrategy):
    """話ごとの挿絵プロンプトを作る。"""

    illustration_type = IllustrationType.EPISODE

    def build_prompt(self, request: IllustrationRequest) -> str:
        override = request.prompt_override
        if override:
            return self._apply_safety(override, request.safety_level, IllustrationType.EPISODE)

        title = self._ctx(request, "title", default="Untitled")
        genre = self._ctx(request, "genre")
        episode_number = request.episode_number
        scene_text = (request.scene_text or "").strip()

        style = self._genre_style(genre)

        if not scene_text:
            # シーン文が無い場合は書籍コンテキストからの汎用プロンプト
            concept = self._ctx(request, "concept")
            parts = [f"Scene illustration for episode {episode_number}."]
            if title:
                parts.append(f"Title: {title}.")
            if genre:
                parts.append(f"Genre: {genre}.")
            if concept:
                parts.append(f"Atmosphere: {concept}.")
            parts.append(style)
            parts.append(
                "Detailed background, cinematic lighting, rich detail, "
                "manga/anime style, no text or letters in image."
            )
            prompt = " ".join(parts)
            return self._apply_safety(prompt, request.safety_level, IllustrationType.EPISODE)

        if len(scene_text) > SCENE_MAX_CHARS:
            scene_text = scene_text[:SCENE_MAX_CHARS] + "..."

        parts = [
            "Detailed illustrative scene from a novel.",
            style,
            f"Scene description: {scene_text}",
            "Cinematic lighting, rich detail, manga/anime style, "
            "no text or letters in image.",
        ]
        prompt = " ".join(parts)
        return self._apply_safety(prompt, request.safety_level, IllustrationType.EPISODE)


__all__ = ["EpisodeStrategy", "SCENE_MAX_CHARS"]
