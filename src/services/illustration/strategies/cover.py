"""表紙イラストのプロンプト戦略。

生成仕様は `src/services/illustration/prompts.py:build_cover_prompt` と
同一。バリエーション（カメラワーク選定）の配列は**重複定義せず**既存
定数を再利用する。
"""

from __future__ import annotations

from src.models.illustration import IllustrationRequest, IllustrationType
from src.services.illustration.strategies.base import PromptStrategy

# 既存の表紙バリエーション（prompts.py の実装提供）
from src.services.illustration.prompts import _COVER_VARIATIONS


class CoverStrategy(PromptStrategy):
    """書籍表紙のプロンプトを作る。"""

    illustration_type = IllustrationType.COVER

    def build_prompt(self, request: IllustrationRequest) -> str:
        override = request.prompt_override
        if override:
            return self._apply_safety(override, request.safety_level, IllustrationType.COVER)

        title = self._ctx(request, "title", default="Untitled")
        genre = self._ctx(request, "genre")
        concept = self._ctx(request, "concept")
        keywords = self._ctx(request, "keywords")

        style = self._genre_style(genre)
        variation = int(request.episode_number or 0)
        camera = _COVER_VARIATIONS[variation % len(_COVER_VARIATIONS)]

        parts = [
            "Professional novel book cover illustration, masterpiece quality.",
            f"Title theme: {title}.",
            style,
            camera,
        ]
        if concept:
            parts.append(f"Story concept: {concept}")
        if keywords:
            parts.append(f"Visual motifs: {keywords}")
        parts.append("High quality, detailed, print-ready, no text or letters in image.")

        prompt = " ".join(parts)
        return self._apply_safety(prompt, request.safety_level, IllustrationType.COVER)


__all__ = ["CoverStrategy"]
