"""src/engine/prompts/erotic_specialist.py
官能シーン専門プロンプトエンジン。
"""
import logging
from string import Template
from typing import Any, Dict, List, Optional

from config.erotic_direct_mappings import get_combined_mappings
from config.erotic_pacing import EroticCurve, EroticBeat
from prompts.erotic.safety_manifest import get_safety_prefix
from src.services.safe_replace import SafeReplacer

logger = logging.getLogger(__name__)

try:
    from config.erotic_parameters import EroticParameters
    from config.erotic_video_patterns import VIDEO_PATTERNS, get_all_pattern_instructions
except ImportError:
    EroticParameters = None
    get_all_pattern_instructions = None


SENSORY_PRIORITY = {
    "touch": "触覚",
    "scent": "嗅覚",
    "breath": "呼吸",
    "gaze": "視線",
    "sound": "聴覚",
    "taste": "味覚",
}

FEELING_LAYERS = [
    "（感覚） body's primal response - 心臓の鼓動、脈の押し、速すぎる呼吸",
    "（解釈） cognitive interpretation - 思考が溶け落ちる、意識が曖昧になる",
    "（評価） emotional evaluation - この感覚が怖いほど心地よい、抵抗できない",
    "（欲動） instinctive impulse - 抗うことをやめたくなる、もっと近くたい",
]


class EroticSpecialist:
    """官能シーンを専門とするプロンプトエンジン。"""

    def build_scene_prompt(
        self,
        curve: EroticCurve,
        context: Dict[str, Any],
        params: Optional["EroticParameters"] = None,
    ) -> str:
        """官能シーン描写用プロンプトを構築する。

        Args:
            curve: 官能曲線
            context: シーンコンテキスト
                - platform_preset: プラットフォームプリセット
                - character_info: キャラクター追加設定
                - scene_setting: シーン追加設定
            params: オプション。EroticParametersインスタンス。
                指定された場合、詳細パラメータを使用したプロンプトを生成する。
        """
        from config.erotic_platform_presets import get_preset
        from config.erotic_vocabulary import get_vocabulary_for_tier
        from prompts.erotic.scene_templates import get_template_for_phase

        preset_name = context.get("platform_preset", "kakuyomu_romance")
        preset = get_preset(preset_name)
        intensity = curve.target_intensity

        vocab = get_vocabulary_for_tier(preset.get("allowed_vocabulary_tier", "mild"))

        metaphor_sample_size = self._get_metaphor_sample_size(intensity, params)
        psychology_sample_size = self._get_psychology_sample_size(intensity, params)

        parts = [get_safety_prefix(), ""]

        parts.append(f"【強度 {intensity}】官能シーン構築プロンプト")
        parts.append("=" * 50)

        if intensity >= 3:
            parts.append(self._build_multi_layer_prompt(intensity, params))

        if params and params.use_video_patterns and get_all_pattern_instructions:
            parts.append(self._build_video_pattern_section(params, intensity))

        for beat in curve.beats:
            parts.append(
                f"\n【{beat.phase.upper()} フェーズ - 欲望レベル: {beat.desire_level}】"
            )
            template = get_template_for_phase(beat.phase)
            filled = Template(template).substitute(
                desire_level=beat.desire_level,
                sensory_focus=", ".join(beat.sensory_focus),
                consent_state=beat.consent_state,
            )
            parts.append(filled)

            if beat.sub_beats:
                for i, sub in enumerate(beat.sub_beats, 1):
                    parts.append(
                        f"\n  └ サブビート{i}: {sub.phase} / 欲望: {sub.desire_level} / "
                        f"感覚: {', '.join(sub.sensory_focus)}"
                    )

            parts.append(self._build_sensory_detail(beat, intensity, params))

        parts.append("\n" + "=" * 50)
        parts.append("【語彙 안내】")
        parts.append(
            f"\n・使用可能な官能比喩表現（{metaphor_sample_size}件）:\n"
            + "\n".join(f"  - {m}" for m in vocab["metaphors"][:metaphor_sample_size])
        )
        parts.append(
            f"\n・使用可能な心理描写表現（{psychology_sample_size}件）:\n"
            + "\n".join(f"  - {p}" for p in vocab["psychology"][:psychology_sample_size])
        )
        parts.append(
            f"\n・使用可能な擬音・擬態語（{min(6 + intensity, 15)}件）:\n"
            + "\n".join(
                f"  - {o}" for o in vocab["onomatopoeia"][:min(6 + intensity, 15)]
            )
        )

        parts.append(self._build_layered_psychology_prompt(intensity, params))
        parts.append(self._build_narrative_flow_prompt(curve))

        if context.get("character_info"):
            parts.append(f"\n・キャラクター追加設定\n{context['character_info']}")
        if context.get("scene_setting"):
            parts.append(f"\n・シーン追加設定\n{context['scene_setting']}")

        if intensity >= 4:
            parts.append(self._build_intense_special_instructions(params))

        return "\n".join(parts)

    def _get_metaphor_sample_size(
        self, intensity: int, params: Optional["EroticParameters"] = None
    ) -> int:
        """metaphor_densityパラメータに応じたサンプルサイズを返す"""
        if params and hasattr(params, "get_metaphor_sample_size"):
            return params.get_metaphor_sample_size()
        base = 8 + intensity * 2
        if params and params.metaphor_density:
            base = int(base * (params.metaphor_density / 50))
        return min(base, 25)

    def _get_psychology_sample_size(
        self, intensity: int, params: Optional["EroticParameters"] = None
    ) -> int:
        """psychology_depthパラメータに応じたサンプルサイズを返す"""
        if params and hasattr(params, "get_psychology_sample_size"):
            return params.get_psychology_sample_size()
        base = 6 + intensity * 2
        if params and params.psychology_depth:
            base = int(base * (params.psychology_depth / 50))
        return min(base, 20)

    def _build_video_pattern_section(
        self, params: "EroticParameters", intensity: int
    ) -> str:
        """映像パターンセクションを生成する"""
        sections = ["", "【映像パターン技術の適用】"]

        if params.video_pattern_preference:
            enabled_patterns = params.video_pattern_preference
        else:
            enabled_patterns = [
                name
                for name, p in VIDEO_PATTERNS.items()
                if p.recommended_intensity <= intensity
            ]

        sections.append(
            get_all_pattern_instructions(
                enabled_patterns, {"include_hints": intensity >= 3}
            )
        )

        return "\n".join(sections)

    def _build_multi_layer_prompt(
        self, intensity: int, params: Optional["EroticParameters"] = None
    ) -> str:
        """多層的心理・感覚描写のための補足プロンプト"""
        lines = [
            "",
            "【多層感覚描写の指示】",
            "各瞬間について以下を段階的に描写すること:",
        ]
        for layer in FEELING_LAYERS:
            lines.append(f"  {layer}")

        if intensity >= 4:
            lines.append("")
            lines.append("【官能の四要素】")
            lines.append("以下の四要素を各ビートで必ず1つ以上言及すること:")
            lines.append("  1. 体温: 肌の熱、汗、（火照り）")
            lines.append("  2. 呼吸: 浅い息、荒い息、息継ぎ")
            lines.append("  3. 湿度: 汗、潤滑、張り付く感触")
            lines.append("  4. 重力: 沈む、浮く、引き寄せられる")
        return "\n".join(lines)

    def _build_sensory_detail(
        self,
        beat: EroticBeat,
        intensity: int,
        params: Optional["EroticParameters"] = None,
    ) -> str:
        """各ビートに対する感覚詳細の補足"""
        lines = []

        if params and params.sensory_weights:
            sorted_senses = sorted(
                beat.sensory_focus,
                key=lambda s: params.sensory_weights.get(s, 50),
                reverse=True,
            )
            for sense in sorted_senses:
                if sense in SENSORY_PRIORITY:
                    weight = params.sensory_weights.get(sense, 50)
                    priority_desc = SENSORY_PRIORITY[sense]
                    lines.append(
                        f"  - {priority_desc}を重点的に描写 (重み: {weight}%)"
                    )
        else:
            for sense in beat.sensory_focus:
                if sense in SENSORY_PRIORITY:
                    priority_desc = SENSORY_PRIORITY[sense]
                    lines.append(f"  - {priority_desc}を重点的に描写")

        if beat.phase == "peak" and intensity >= 4:
            lines.append("  ※ ピーク時: 複数の感覚を同時に（同調して）描写する")
        elif beat.phase == "afterglow":
            lines.append("  ※ 余韻時: 感覚の消退と共存の双方を描写する")

        if beat.desire_level >= 70:
            lines.append(f"  ※ 高欲望時: 理性の揺らぎ・判断力の低下を描写")
        elif beat.desire_level >= 85:
            lines.append(f"  ※ 極限時: 自我の消失・抵抗の放棄を描写")

        return "\n".join(lines) if lines else ""

    def _build_layered_psychology_prompt(
        self, intensity: int, params: Optional["EroticParameters"] = None
    ) -> str:
        """心理描写の深度を確保する補足"""
        if intensity < 3:
            return ""

        lines = [
            "",
            "【心理深層への誘導】",
        ]

        depth_addition = ""
        if params and params.psychology_depth:
            if params.psychology_depth >= 80:
                depth_addition = "（最深レベル: 自我の完全なる崩壊・存在の溶解を含む）"
            elif params.psychology_depth >= 60:
                depth_addition = "（深層レベル: 抵抗の放棄・快楽への渇望を含む）"
            elif params.psychology_depth >= 40:
                depth_addition = "（標準レベル: 陶酔・恍惚を含む）"

        if intensity >= 4:
            lines.append(
                f"以下の心理プロセスを各シーンで最低1つは含めること{depth_addition}:"
            )
            lines.append("  - 「思考が停止する」または「思考が暴走する」")
            lines.append("  - 「自我の境界が曖昧になる」")
            lines.append("  - 「時間感覚の歪み・消失」")
            lines.append("  - 「快楽と苦痛の境界の消失」")
        elif intensity >= 3:
            lines.append(
                f"以下の心理表現を各シーンで最低1つは使用すること{depth_addition}:"
            )
            lines.append("  - 陶酔、恍惚、自失、快楽の飽和")
            lines.append("  - 抗えない吸引力、抵抗の糸が切れる")
        return "\n".join(lines)

    def _build_narrative_flow_prompt(self, curve: EroticCurve) -> str:
        """溜めと解放のフロー確保"""
        lines = [
            "",
            "【構成の指示】",
        ]

        build_beats = [b for b in curve.beats if b.phase == "build"]
        peak_beats = [b for b in curve.beats if b.phase == "peak"]
        afterglow_beats = [b for b in curve.beats if b.phase == "afterglow"]

        if len(build_beats) > 1:
            lines.append(
                f"  - 溜め（build）は{len(build_beats)}段階で段階的に構築すること"
            )
        if len(peak_beats) > 1:
            lines.append(
                f"  - ピーク（peak）は{len(peak_beats)}回繰り返され、各レベルで極限を描写すること"
            )

        lines.append("  - 各フェーズ間の移行は自然かつ必然性があること")
        lines.append("  - 余韻（afterglow）は感情の沈降と次話への伏線を含むこと")

        return "\n".join(lines)

    def _build_intense_special_instructions(
        self, params: Optional["EroticParameters"] = None
    ) -> str:
        """強度5専用の追加指示"""
        density_addition = ""
        if params and params.metaphor_density:
            if params.metaphor_density >= 80:
                density_addition = (
                    "\n8. 比喩の密度を上げ、感覚の多层構造を明示的に描写すること"
                )
            elif params.metaphor_density <= 30:
                density_addition = (
                    "\n8. 比喩は控えめにし、直接的な感覚描写を重視すること"
                )

        return f"""
【強度5（過激）専用の品質基準】
1. 身体的感觉の「変容」を描写せよ（通常の感覚描写ではない）
2. 精神の「崩壊」または「溶解」を描写せよ（正常な心理状態ではない）
3. 快楽の「飽和」または「決壊」を描写せよ（穏やかな快感ではない）
4. 自我の「喪失」を描写せよ（意識が清明な状態ではない）
5. 比喩は身体的・感覚的な根拠を持つこと（抽象的表現は避ける）
6. 「体温」「呼吸」「脈拍」「湿度」の4要素を統合すること
7. 「滞留」（反復的な高まり）を許容し、单一のピークで終わらないこと{density_addition}
"""

    def build_aftercare_prompt(self, context: Dict[str, Any]) -> str:
        """
        余韻（afterglow）生成プロンプトを構築する。

        Args:
            context: シーンコンテキスト
                - desire_level: 欲望レベル（デフォルト20）
                - sensory_focus: 感覚の焦点（デフォルト "touch, gaze"）
                - consent_state: 同意状態（デフォルト "established"）
                - next_episode_hint: 次話への伏線テキスト
                - intensity: 強度レベル（デフォルト2）

        生成後は AfterglowEvaluator.evaluate() で品質検証すること。
        品質閾値: 最低2段落 / 最低400文字 / 感情沈降表現 / 距離再確認表現 / 次話伏線
        """
        from prompts.erotic.scene_templates import get_template_for_phase

        intensity = context.get("intensity", 2)
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
            "・余韻描写の品質基準:",
            "  - 最低2段落、最低400字で表現すること",
            "  - 感情の沈降（陶酔→平静）を段階的に描写すること",
            "  - キャラクター間の心理的・物理的な距離を再確認すること",
            "  - 次の話への伏線を必ず1つ以上含めること",
            "  - 体の温度・湿度・緊張感の消退を描写すること",
        ]

        if intensity >= 4:
            parts.append("")
            parts.append("【強度4以上の余韻では以下も含むこと】")
            parts.append("  - 意識が清明に戻るプロセスの描写")
            parts.append("  - 快楽の余韻と現実感覚の併存")
            parts.append("  - 自己確認行動（相手を探す、距離確認）")
            parts.append("  - 精神的充足感または罪悪感のいずれか")

        if context.get("next_episode_hint"):
            parts.append(f"- 次話のヒント: {context['next_episode_hint']}")
        return "\n".join(parts)

    def metaphor_filter(
        self, raw_scene: str, intensity: int, vocab: Optional[Dict[str, Any]] = None
    ) -> str:
        """過剰な直接表現を比喩表現に置換する。

        Args:
            raw_scene: フィルタリング対象テキスト
            intensity: 強度レベル
            vocab: オプション。比喩表現辞書（未使用、後方互換のため残す）。
        """
        combined = get_combined_mappings()
        replacer = SafeReplacer(combined)
        result = replacer.replace(raw_scene)

        if intensity < 3:
            return result

        return result
