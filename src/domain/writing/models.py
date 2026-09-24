"""Shared data models for the writing domain."""

import re
from typing import Any
from pydantic import BaseModel


def clean_writing_response(text: str) -> str:
    """思考ログを除去して本文を整形する"""
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL)
    return text.strip()


class WritingGenerationContext(BaseModel):
    """執筆生成コンテキストモデル"""
    sys_inst: str = ""
    fw_prompt: str = ""
    pov_instruction: str = ""
    expanded_beats: str = ""
    feedback_patch: str = ""
    style_key: str = "style_web_standard"
    target_word_count: int = 2000
    enable_polishing: bool = True
    prose_sample: str = ""
    plot: Any | None = None

    def build_sys_inst(self) -> str:
        parts = [self.sys_inst]
        if self.pov_instruction:
            parts.append(self.pov_instruction)
        if self.feedback_patch:
            parts.append(f"\n\n【🚨自己評価フィードバックパッチ】\n{self.feedback_patch}")
        return "\n\n".join(parts)

    def build_fw_prompt(self, suffix: str = "") -> str:
        parts = [self.fw_prompt]
        if self.pov_instruction:
            parts.append(self.pov_instruction)
        if self.expanded_beats:
            parts.append(
                f"\n\n【📝 物理動作ビート分解（絶対遵守）】\n以下のビートに従って、各ビートの文字数を意識しShow, Don't Tellを徹底しながら執筆してください：\n{self.expanded_beats}\n"
            )
        if suffix:
            parts.append(suffix)
        return "\n\n".join(parts)


from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RegenerationAction:
    """再生成アクション定義"""
    focus_dimensions: list[str]
    context_builder_focus: list[str]
    writing_focus: list[str]
    illustration_focus: list[str]
    priority: int
    anti_ai_loop_result: dict = field(default_factory=dict)


DIMENSION_ACTIONS = {
    "structure": RegenerationAction(
        focus_dimensions=["structure"],
        context_builder_focus=["arc_boundary", "tempo"],
        writing_focus=["plot_adherence", "pacing"],
        illustration_focus=[],
        priority=1,
    ),
    "coherency": RegenerationAction(
        focus_dimensions=["coherency"],
        context_builder_focus=["character_voice", "world_rules"],
        writing_focus=["dialogue_consistency", "terminology"],
        illustration_focus=[],
        priority=2,
    ),
    "factual_grounding": RegenerationAction(
        focus_dimensions=["factual_grounding"],
        context_builder_focus=["rag_entities", "historical_accuracy"],
        writing_focus=["setting_consistency", "term_usage"],
        illustration_focus=[],
        priority=3,
    ),
    "visual_textual_synergy": RegenerationAction(
        focus_dimensions=["visual_textual_synergy"],
        context_builder_focus=[],
        writing_focus=["scene_focus"],
        illustration_focus=["prompt_regeneration", "emotion_tone_match"],
        priority=4,
    ),
    "reader_experience": RegenerationAction(
        focus_dimensions=["reader_experience"],
        context_builder_focus=[],
        writing_focus=["hook_enhancement", "cliffhanger", "emotional_arc"],
        illustration_focus=[],
        priority=5,
    ),
    "anti_ai_correction": RegenerationAction(
        focus_dimensions=["anti_ai_correction"],
        context_builder_focus=[],
        writing_focus=[],
        illustration_focus=[],
        priority=0,
    ),
}