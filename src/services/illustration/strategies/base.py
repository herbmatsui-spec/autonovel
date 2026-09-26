"""プロンプト構築戦略の基底クラス。

種別（表紙 / 立ち絵 / 挿絵 / 6コマ / 24コマ）の差分はすべてこの配下の
戦略クラスに閉じ込める。統合エンジン本体（`UnifiedIllustrationGenerator`）
は `IllustrationType` の `if` 分岐を持たない。

**重複定義の禁止**: ジャンルスタイルヒントは `src/services/illustration/prompts.py`
の `_genre_hint` を、R15 修飾は `apply_safety_modifier` を再利用する。
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence

from src.models.illustration import IllustrationRequest, IllustrationType, SafetyLevel
from src.services.illustration.config import UnifiedIllustrationConfig

# 全種別に共通で課す禁止句（文字描画・透かし等）
COMMON_NEGATIVE = (
    "text, letters, watermark, signature, blurry, low resolution, "
    "3d render, photograph, distorted faces, extra limbs"
)

# 複数コマ（漫画シート）で禁じる語
MULTI_PANEL_NEGATIVE = "single panel, non-sequential, missing panels, uneven gutters"


class PromptStrategy(ABC):
    """種別ごとのプロンプトビルダ。"""

    #: この戦略が扱う種別（レジストリ検証用）
    illustration_type: Optional[IllustrationType] = None

    def __init__(
        self,
        config: UnifiedIllustrationConfig,
        llm: Any = None,
    ) -> None:
        self.config = config
        #: 任意。LLM 要約を使いたい戦略（Yonkoma 系）が参照する。
        self.llm = llm

    # ---- 必須実装 ----

    @abstractmethod
    def build_prompt(self, request: IllustrationRequest) -> str:
        """この種別用のプロンプトを組み立てる。"""
        raise NotImplementedError

    # ---- 共通処理 ----

    def build_negative_prompt(self, request: IllustrationRequest) -> str:
        """種別に応じたネガティブプロンプトを返す。"""
        type_value = self._type_value(request.illustration_type)
        if type_value in ("yonkoma", "manga_24panel"):
            return f"{COMMON_NEGATIVE}, {MULTI_PANEL_NEGATIVE}"
        return COMMON_NEGATIVE

    def regenerate_prompt(
        self,
        request: IllustrationRequest,
        action: Any = None,
    ) -> Dict[str, Any]:
        """再生成フォーカス（visual_textual_synergy 等）による強化。

        既存の `IllustrationAgent.regenerate_prompts` と同じ書式を返す。
        """
        original = request.prompt_override or self.build_prompt(request)
        scene_text = getattr(request, "scene_text", "") or (
            request.book_context or {}
        ).get("scene_text", "")

        enhancements: List[str] = []
        params = getattr(action, "params", None) or {}
        if isinstance(action, dict):
            params = action.get("params", params)

        if params.get("refocus_on_text_entities") and scene_text:
            entities = list(dict.fromkeys(re.findall(r"[一-龯ァ-ヴー]{2,}", scene_text)))[:10]
            if entities:
                enhancements.append(f"Key entities to include: {', '.join(entities)}")

        if params.get("match_emotional_tone") and scene_text:
            tone = detect_emotional_tone(scene_text)
            if tone != "neutral":
                desc = "bright and hopeful" if tone == "positive" else "dark and somber"
                enhancements.append(f"Emotional tone: {desc}")

        enhanced = original
        if enhancements:
            enhanced = original + " | ENHANCEMENTS: " + "; ".join(enhancements)

        return {
            "status": "success",
            "original_prompt": original,
            "enhanced_prompt": enhanced,
            "enhancements_applied": enhancements,
            "focus": "visual_textual_synergy",
        }

    # ---- ヘルパ ----

    @staticmethod
    def _type_value(illustration_type: Any) -> str:
        try:
            return str(illustration_type.value)
        except AttributeError:
            return str(illustration_type)

    @staticmethod
    def _book_context(request: IllustrationRequest) -> Dict[str, str]:
        return request.book_context or {}

    def _ctx(
        self,
        request: IllustrationRequest,
        *keys: str,
        default: str = "",
    ) -> str:
        """`book_context` から優先キーを順に評価して、最初に取れた値を返す。"""
        ctx = self._book_context(request)
        for key in keys:
            value = ctx.get(key)
            if value:
                return str(value)
        return default

    def _genre_style(self, genre: str) -> str:
        """ジャンル別スタイルヒント（`prompts._genre_hint` を単一ソースとして再利用）。"""
        from src.services.illustration.prompts import _genre_hint

        return _genre_hint(genre or "")

    def _apply_safety(
        self,
        prompt: str,
        safety_level: Any,
        illustration_type: Any,
    ) -> str:
        """R15 修飾（`prompts.apply_safety_modifier` を単一ソースとして再利用）。"""
        from src.services.illustration.prompts import apply_safety_modifier

        normalized = _coerce_safety(safety_level)
        return apply_safety_modifier(prompt, normalized, illustration_type)

    def _apply_yonkoma_safety(self, prompt: str, safety_level: Any) -> str:
        """4コマ/24コマ系用の R15 修飾（`prompts.apply_yonkoma_safety_modifier` 再利用）。"""
        from src.services.illustration.prompts import apply_yonkoma_safety_modifier

        return apply_yonkoma_safety_modifier(prompt, _coerce_safety(safety_level))

    def _aspect_ratio(self, request: IllustrationRequest) -> str:
        return request.aspect_ratio or self.config.aspect_ratio_for(request.illustration_type)

    def _is_multi_panel(self, request: IllustrationRequest) -> bool:
        return self._type_value(request.illustration_type) in ("yonkoma", "manga_24panel")


def _coerce_safety(safety_level: Any) -> SafetyLevel:
    """str / enum 混在を `SafetyLevel` に正規化する。"""
    if isinstance(safety_level, SafetyLevel):
        return safety_level
    value = getattr(safety_level, "value", safety_level)
    try:
        return SafetyLevel(str(value))
    except ValueError:
        return SafetyLevel.BLOCK_SOME


_POSITIVE_WORDS = ("喜", "笑", "幸", "楽", "愛", "希望", "輝", "明")
_NEGATIVE_WORDS = ("悲", "泣", "苦", "痛", "憎", "絶望", "暗", "闇", "恐")


def detect_emotional_tone(text: str) -> str:
    """本文の語彙から感情トーンを Rough 判定する（positive/negative/neutral）。"""
    if not text:
        return "neutral"
    positive = sum(text.count(w) for w in _POSITIVE_WORDS)
    negative = sum(text.count(w) for w in _NEGATIVE_WORDS)
    if positive > negative:
        return "positive"
    if negative > positive:
        return "negative"
    return "neutral"


def split_paragraphs(text: str, min_length: int = 8) -> List[str]:
    """本文を段落／文単位へ分割する（既存ヒューリスティックと同じ規則）。"""
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"\n{2,}|[。！？]\s*", text) if p.strip()]
    return [p for p in parts if len(p) >= min_length]


def distribute_paragraphs(paragraphs: Sequence[str], panels: int) -> List[str]:
    """段落を `panels` 個へ均等配分する（不足分は末尾で埋める）。"""
    panels = max(1, int(panels))
    usable = [p for p in paragraphs if p]
    if not usable:
        return ["" for _ in range(panels)]
    if len(usable) >= panels:
        step = len(usable) / panels
        return [usable[min(int(i * step), len(usable) - 1)] for i in range(panels)]
    padded = list(usable)
    while len(padded) < panels:
        padded.append(usable[-1])
    return padded[:panels]


__all__ = [
    "COMMON_NEGATIVE",
    "MULTI_PANEL_NEGATIVE",
    "PromptStrategy",
    "detect_emotional_tone",
    "distribute_paragraphs",
    "split_paragraphs",
]
