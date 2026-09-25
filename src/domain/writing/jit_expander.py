"""src/domain/writing/jit_expander.py - JIT Beat Expander & Editor Synchronizer (v5.2.0)

Coarse-to-Fine二段階プロット（粗大スケルトン→精密マイクロ設計図）のJIT展開、
およびStudioエディタ（TipTap）とビート情報の双方向同期・文字数/会話率メトリクスを提供する。
"""

from __future__ import annotations

import re
from typing import Any
from pydantic import BaseModel, Field


class EditorMetrics(BaseModel):
    """本文エディタのリアルタイム分析メトリクス."""

    char_count: int = 0
    dialogue_char_count: int = 0
    dialogue_ratio: float = 0.0
    ruby_count: int = 0


class JITBeatExpander:
    """エディタ編集テキストとビートシートの整合性を維持・分析するJITエンジン."""

    @staticmethod
    def calculate_metrics(text: str) -> EditorMetrics:
        """文字数、会話文（「」）の割合、ルビ記法数を計算する."""
        if not text:
            return EditorMetrics()

        clean_text = text.replace("\r", "")
        char_count = len(clean_text)

        # 会話文（「 ... 」）の抽出
        dialogue_matches = re.findall(r"「([^」]*)」", clean_text)
        dialogue_char_count = sum(len(m) for m in dialogue_matches)
        dialogue_ratio = round(dialogue_char_count / char_count, 3) if char_count > 0 else 0.0

        # ルビ記法（|漢字《ルビ》）
        ruby_matches = re.findall(r"\|[^《\n]+《[^》\n]+》", clean_text)
        ruby_count = len(ruby_matches)

        return EditorMetrics(
            char_count=char_count,
            dialogue_char_count=dialogue_char_count,
            dialogue_ratio=dialogue_ratio,
            ruby_count=ruby_count,
        )

    @staticmethod
    def sync_editor_content_with_beats(
        editor_text: str,
        current_beats: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """エディタ本文とビート情報の同期更新."""
        metrics = JITBeatExpander.calculate_metrics(editor_text)

        # ビート毎の進捗推定（文字数配分）
        total_beats = len(current_beats) if current_beats else 1
        allocated_target = metrics.char_count // total_beats

        updated_beats = []
        for i, beat in enumerate(current_beats):
            b = dict(beat)
            b["current_chars"] = allocated_target
            b["completed"] = metrics.char_count >= (i + 1) * (allocated_target or 1)
            updated_beats.append(b)

        return {
            "metrics": metrics.model_dump(),
            "updated_beats": updated_beats,
            "is_synchronized": True,
        }


__all__ = ["EditorMetrics", "JITBeatExpander"]
