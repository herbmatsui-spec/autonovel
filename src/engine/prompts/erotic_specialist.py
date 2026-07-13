"""src/engine/prompts/erotic_specialist.py
官能シーン専門プロンプトエンジン。
"""
import logging
from string import Template
from typing import Any, Dict, Optional

from config.erotic_direct_mappings import get_combined_mappings
from config.erotic_pacing import EroticCurve
from prompts.erotic.safety_manifest import get_safety_prefix
from src.services.safe_replace import SafeReplacer

logger = logging.getLogger(__name__)


class EroticSpecialist:
    """官能シーンを専門とするプロンプトエンジン。低性能LLMでも安定して再現可能な出力のため。"""

    def build_scene_prompt(self, curve: EroticCurve, context: Dict[str, Any]) -> str:
        """官能・シーン描写用プロンプトを構築する。
        
        修正履歴(2026-07-08):
        - vocab取得を関数入口付近で1回だけ取得し使い回し（重複呼び出しを削除）
        """
        from config.erotic_platform_presets import get_preset
        from config.erotic_vocabulary import get_vocabulary_for_tier
        from prompts.erotic.scene_templates import get_template_for_phase

        preset_name = context.get("platform_preset", "kakuyomu_romance")
        preset = get_preset(preset_name)

        # vocab取得は関数の先頭で1回だけ（重複を削除）
        vocab = get_vocabulary_for_tier(preset.get("allowed_vocabulary_tier", "mild"))

        parts = [get_safety_prefix(), ""]

        for beat in curve.beats:
            template = get_template_for_phase(beat.phase)
            filled = Template(template).substitute(
                desire_level=beat.desire_level,
                sensory_focus=", ".join(beat.sensory_focus),
                consent_state=beat.consent_state,
            )
            parts.append(filled)

        # 語彙の追加案内
        parts.append("\n・使用可能な官能比喩表現\n" + "\n".join(f"- {m}" for m in vocab["metaphors"][:5]))
        parts.append("\n・使用可能な心理描写表現\n" + "\n".join(f"- {p}" for p in vocab["psychology"][:5]))

        # キャラクター・シーン追加情報
        if context.get("character_info"):
            parts.append(f"\n・キャラクター追加設定\n{context['character_info']}")
        if context.get("scene_setting"):
            parts.append(f"\n・シーン追加設定\n{context['scene_setting']}")

        return "\n".join(parts)

    def build_aftercare_prompt(self, context: Dict[str, Any]) -> str:
        """
        余韻（afterglow）生成プロンプトを構築する。

        Args:
            context: シーンコンテキスト
                - desire_level: 欲望レベル（デフォルト20）
                - sensory_focus: 感覚の焦点（デフォルト "touch, gaze"）
                - consent_state: 同意状態（デフォルト "established"）
                - next_episode_hint: 次話への伏線テキスト

        生成後は AfterglowEvaluator.evaluate() で品質検証すること。
        品質閾値: 最低2段落 / 最低400文字 / 感情沈降表現 / 距離再確認表現 / 次話伏線
        """
        from prompts.erotic.scene_templates import get_template_for_phase

        template = get_template_for_phase("afterglow")
        filled = Template(template).substitute(
            desire_level=context.get("desire_level", 20),
            sensory_focus=context.get("sensory_focus", "touch, gaze"),
            consent_state=context.get("consent_state", "established"),
        )
        parts = [
            get_safety_prefix(),
            "",
            filled,
            "",
            "・この余韻描写は最低2段落、最低400字で表現すること",
            "・次の話への伏線を必ず1つ以上含めること",
            "・キャラクター間の心理的・物理的な距離再確認を表現すること",
        ]
        if context.get("next_episode_hint"):
            parts.append(f"- 次話のヒント: {context['next_episode_hint']}")
        return "\n".join(parts)

    def metaphor_filter(self, raw_scene: str, intensity: int, vocab: Optional[Dict[str, Any]] = None) -> str:
        """過剰な直接表現を比喩表現に置換する。
        
        Args:
            raw_scene: フィルタリング対象テキスト
            intensity: 強度レベル
            vocab: オプション。比喩表現辞書（未使用、後方互換のため残す）。
        """
        combined = get_combined_mappings(intensity)
        replacer = SafeReplacer(combined)
        return replacer.replace(raw_scene)
