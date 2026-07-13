from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from kernels.base import KernelBase
from prompts.hegemony_persona import HEGEMONY_PERSONA


@dataclass
class PowerDynamic:
    """
    キャラクター間の権力関係と、その内面に潜む脆弱性を定義する。
    """
    dominant_char: str
    submissive_char: str
    hierarchy_level: int  # 1-5 (Persona定義のレベルに準拠)
    structural_gap: float # 権力格差 (0-100)
    internal_fragility: float # 支配側の内面的な脆さ/脆弱性 (0-100)
    keystone_vulnerability: str # 権力構造を崩壊させる唯一の急所（キーワード/記憶）

class HegemonyKernel(KernelBase):
    """
    社会的地位と内面的脆弱性の乖離を管理し、
    権力構造の維持と、その崩壊によるドラマを演出するエンジン。
    """

    def __init__(self, **kwargs):
        self.state_value = 0.0 # Interaction Matrix用
        super().__init__(**kwargs)
        self.persona = HEGEMONY_PERSONA
        self.patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[str, List[Dict]]:
        import json
        import os
        path = "config/data/hegemony_patterns.json"
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    async def execute(self, context):
        if await self.should_intervene(context):
            return await self.generate_hegemony_event(context)
        return None

    async def should_intervene(self, context) -> bool:
        """
        権力構造の固定化、または支配側の脆弱性が刺激されるタイミングを検知して介入する。
        物語の状態（Narrative State）に応じて、介入の閾値を動的に調整する。
        """
        analytics = getattr(context, 'analytics', None)
        if not analytics:
            return False

        # 物語状態の取得
        narrative_state = getattr(context, 'narrative_state', None)

        # 優先カーネルの確認
        priority_kernels = context.global_state.get('priority_kernels', [])
        is_priority = "hegemony" in priority_kernels

        # 状態に応じた介入感度の調整
        # CONFLICT や CLIMAX では権力構造の揺らぎを積極的に演出する
        sensitivity_multiplier = 1.0
        if narrative_state == NarrativeState.CONFLICT:
            sensitivity_multiplier = 1.3
        elif narrative_state == NarrativeState.CLIMAX:
            sensitivity_multiplier = 1.5
        elif narrative_state == NarrativeState.DAILY:
            sensitivity_multiplier = 0.7

        if is_priority:
            sensitivity_multiplier *= 1.4

        # 1. 権力による停滞 (Static Dominance)
        # 支配的すぎて緊張感が消失し、物語が一方的に進行している場合
        if getattr(analytics, 'is_too_dominant', False):
            return True

        # 2. 権力の揺らぎ (Power Shaking)
        # 緊張度が高まり、支配者の「仮面」が剥がれかかる瞬間
        tension = getattr(analytics, 'tension', 0)
        curiosity = getattr(analytics, 'curiosity', 0)
        resonance = getattr(analytics, 'resonance', 0)

        # 高緊張 + 疑惑/好奇心が支配者の急所に触れそうな場合
        # 優先カーネルである場合は閾値を緩和
        t_thresh = 70 if not is_priority else 50
        c_thresh = 60 if not is_priority else 40
        if tension > t_thresh and curiosity > c_thresh:
            return True

        # 高共鳴による境界喪失: 権力勾配が意味をなさなくなる瞬間
        res_thresh = 80 if not is_priority else 60
        if resonance > res_thresh:
            return True

        # 3. 内面的脆弱性の漏出 (Fragility Leak)
        # 低緊張時であっても、支配側の脆さが不意に露呈するタイミング
        # (analyze_power_gapで算出される internal_fragility を参照)
        chars = getattr(context, 'characters', {})
        if chars:
            # 代表的な二者のダイナミクスを確認
            char_list = list(chars.keys())
            if len(char_list) >= 2:
                dynamic = self.analyze_power_gap(char_list[0], char_list[1], context)
                # 優先カーネルである場合は脆弱性の露呈を促す
                f_thresh = 70 if not is_priority else 50
                if dynamic.internal_fragility > f_thresh and tension < 30:
                    return True

        return False

    async def generate_hegemony_event(self, context):
        """
        権力構造の維持、またはその「揺らぎ」を演出する。
        """
        chars = getattr(context, 'characters', {})
        if not chars or len(chars) < 2:
            return None

        char_list = list(chars.keys())
        dynamic = self.analyze_power_gap(char_list[0], char_list[1], context)

        # 1. 介入タイプの決定
        analytics = getattr(context, 'analytics', None)
        tension = getattr(analytics, 'tension', 0) if analytics else 0

        # 物語状態に基づいたイベントタイプの重み付け
        narrative_state = getattr(context, 'narrative_state', None)

        if tension > 85:
            event_type = "COLLAPSE"
        elif tension > 50 or dynamic.internal_fragility > 50:
            # CONFLICT状態ではより激しい SHAKE を、DAILYでは緩やかな SHAKE を選択
            event_type = "SHAKE"
        elif narrative_state == NarrativeState.CONFLICT:
            # CONFLICT状態なら、緊張度が低くても権力関係を揺さぶるイベントを発生させやすくする
            event_type = "SHAKE" if dynamic.internal_fragility > 30 else "REINFORCE"
        else:
            event_type = "REINFORCE"

        # 2. パターンライブラリから最適な演出を選択
        patterns_list = self.patterns.get(event_type, [])
        if not patterns_list:
            return {"event_type": event_type, "dynamic": dynamic, "instruction": "Generic power event"}

        # 簡易的な選択ロジック: 脆弱性や緊張度に基づくフィルタリング
        # 実際にはより詳細なスコアリングを行う
        selected_pattern = patterns_list[0] # デフォルト
        for p in patterns_list:
            if "high_tension" in p.get("triggers", []) and tension > 70:
                selected_pattern = p
                break
            if "resonance_increase" in p.get("triggers", []) and getattr(analytics, 'resonance', 0) > 70:
                selected_pattern = p
                break

        # POVとEnigmaへの連携メタデータを追加
        pov_char = getattr(context, 'pov_character', None)
        interpretation = self._calculate_pov_interpretation(pov_char, dynamic, event_type, selected_pattern)

        # 視点による解釈の齟齬（誤読層）を追加
        misinterpretation = self._calculate_misinterpretation(pov_char, dynamic, event_type, interpretation)

        # 指示書の構築
        base_instruction = f"Implement a {event_type} event using pattern {selected_pattern['pattern_id']}. Focus on {dynamic.keystone_vulnerability}. POV: {pov_char}'s interpretation: {interpretation['mode']}. Misinterpretation: {misinterpretation['misread_as']}."

        # 監査ループの実行
        final_scene = await self._run_hegemony_audit(context, base_instruction, event_type, dynamic, interpretation, misinterpretation)

        return {
            "event_type": event_type,
            "pattern_id": selected_pattern["pattern_id"],
            "dynamic": dynamic,
            "guidelines": selected_pattern["guidelines"],
            "impact": selected_pattern["impact"],
            "pov_interpretation": interpretation,
            "misinterpretation": misinterpretation,
            "enigma_link": {
                "type": "POWER_SHAKE" if event_type == "SHAKE" else "POWER_COLLAPSE",
                "secret_exposed": dynamic.keystone_vulnerability if event_type in ["SHAKE", "COLLAPSE"] else None,
                "witness": pov_char
            },
            "scene": final_scene,
            "instruction": base_instruction
        }

    async def _run_hegemony_audit(self, context, instruction, event_type, dynamic, interpretation, misinterpretation, max_retries: int = 2):
        """
        生成されたシーンが権力構造およびPOVの誤読と整合しているか監査し、必要に応じて修正させる。
        """
        from prompts.manager import PromptManager

        # 1. 初回生成
        current_instruction = instruction
        scene = await context.llm.generate(f"{self.persona}\n\n{current_instruction}")

        for attempt in range(max_retries):
            # 監査プロンプトのレンダリング
            prompt_template = PromptManager.get_prompt("hegemony_audit_prompt.j2")
            audit_input = {
                "dynamic": dynamic,
                "event_type": event_type,
                "pov_interpretation": interpretation,
                "misinterpretation": misinterpretation,
                "scene_text": scene
            }
            audit_prompt = prompt_template.render(**audit_input)

            # 監査実行
            audit_result = await context.llm.generate(audit_prompt)

            if "[PASS]" in audit_result:
                return scene

            # FAILの場合、修正指示を抽出して再生成
            current_instruction = f"{instruction}\n\nAudit Feedback: {audit_result}\n\nPlease rewrite the scene to fix these structural contradictions."
            scene = await context.llm.generate(f"{self.persona}\n\n{current_instruction}")

        return scene

    def analyze_power_gap(self, char_a: str, char_b: str, context) -> PowerDynamic:
        """
        二者の社会的地位と心理的優位性を分析し、PowerDynamic オブジェクトを生成する。
        """
        chars = getattr(context, 'characters', {})
        char_a_data = chars.get(char_a, {})
        char_b_data = chars.get(char_b, {})

        # 社会的地位の数値化 (簡易実装)
        # 本来は domain_profile や archetype から算出
        rank_a = char_a_data.get('social_rank', 3)
        rank_b = char_b_data.get('social_rank', 3)

        # 支配者の決定
        if rank_a >= rank_b:
            dom, sub = char_a, char_b
            gap = max(0, rank_a - rank_b) * 20.0
        else:
            dom, sub = char_b, char_a
            gap = max(0, rank_b - rank_a) * 20.0

        # 内面的脆弱性の算出
        # 精神的な不安定さや、隠したい秘密の深さなどを反映
        fragility = char_a_data.get('internal_fragility', 30.0) if dom == char_a else char_b_data.get('internal_fragility', 30.0)

        # 急所の特定
        vulnerability = char_a_data.get('keystone_vulnerability', "Unknown vulnerability") if dom == char_a else char_b_data.get('keystone_vulnerability', "Unknown vulnerability")

        return PowerDynamic(
            dominant_char=dom,
            submissive_char=sub,
            hierarchy_level=int(max(1, min(5, (rank_a + rank_b) / 2))),
            structural_gap=gap,
            internal_fragility=fragility,
            keystone_vulnerability=vulnerability
        )

    def _calculate_misinterpretation(self, pov_char: Optional[str], dynamic: PowerDynamic, event_type: str, interpretation: Dict) -> Dict:
        """
        本来の権力変動をPOVキャラクターがどう誤読するかを計算する。
        """
        if not pov_char:
            return {"misread_as": None, "dissonance_level": 0}

        # 誤読マッピング: (本来の解釈mode) -> (誤読後の解釈)
        misread_map = {
            "discovery": {
                "misread_as": "Affection/Softness",
                "logic": "支配者の脆弱性を、自分への好意や甘えと誤認する"
            },
            "panic": {
                "misread_as": "Momentary Lapse",
                "logic": "支配者の崩壊を、単なる一時的な情緒不安定と過小評価する"
            },
            "suspicion": {
                "misread_as": "Calculation",
                "logic": "相手の揺らぎを、自分を罠にかけるための高度な演技と疑う"
            },
            "liberation": {
                "misread_as": "Temptation",
                "logic": "得られた自由を、さらなる支配への誘い（罠）と感じて躊躇する"
            }
        }

        current_mode = interpretation.get("mode")
        misread_data = misread_map.get(current_mode, {"misread_as": None, "logic": None})

        # 構造的格差が大きい場合、誤読レベルが高まる
        dissonance = (dynamic.structural_gap / 100.0) * 50.0 if current_mode in misread_map else 0

        return {
            "misread_as": misread_data["misread_as"],
            "logic": misread_data["logic"],
            "dissonance_level": dissonance
        }

    def _calculate_pov_interpretation(self, pov_char: Optional[str], dynamic: PowerDynamic, event_type: str, pattern: Dict) -> Dict:
        """
        POVキャラクターが権力構造の変化をどう解釈するかを計算する。
        """
        if not pov_char:
            return {"mode": "neutral", "reaction": "Observation of power shift"}

        # POVが誰であるかによって解釈を変える
        if pov_char == dynamic.dominant_char:
            # 支配者視点
            if event_type == "COLLAPSE":
                return {"mode": "panic", "reaction": "Shock and desperation as the structure crumbles"}
            if event_type == "SHAKE":
                return {"mode": "anxiety", "reaction": "Fear of exposure and urgent need to regain control"}
            return {"mode": "satisfaction", "reaction": "Confirmation of absolute authority"}

        elif pov_char == dynamic.submissive_char:
            # 被支配者視点
            if event_type == "COLLAPSE":
                return {"mode": "liberation", "reaction": "Euphoria and newfound power as the oppressor falls"}
            if event_type == "SHAKE":
                return {"mode": "discovery", "reaction": "Intense curiosity and calculated hope upon finding a weakness"}
            return {"mode": "resignation", "reaction": "Internalization of helplessness and submission"}

        else:
            # 第三者視点
            if event_type == "COLLAPSE":
                return {"mode": "astonishment", "reaction": "Bafflement at the sudden reversal of status"}
            if event_type == "SHAKE":
                return {"mode": "suspicion", "reaction": "Sensing an underlying tension that doesn't match the surface hierarchy"}
                return {"mode": "acceptance", "reaction": "Recognition of the established order"}


    # ==========================================
    # 商用役割ベースの支配力変動関数（ステップ13）
    # ==========================================
    def role_based_power_shift(
        character_roles: List[str],
        current_power: float,
        story_progress: float,  # 0.0 - 1.0
        flip_timing_config: Optional[Dict] = None
    ) -> Tuple[float, str, List[str]]:
        """商用役割に応じて権力値を動的に変動させる
        
        Args:
            character_roles: キャラクターの商用役割リスト
            current_power: 現在の権力値（0-100）
            story_progress: 物語の進行度（0.0-1.0）
            flip_timing_config: STATUS_FLIP_TRIGGER用のタイミング設定
        
        Returns:
            (新しい権力値, 変動タイプ, 発生イベントリスト)
        """
        from config.archetypes import GROWTH_INVESTMENT_PHASES, CommercialRole

        new_power = current_power
        shift_type = "stable"
        events = []

        for role in character_roles:
            role_enum = role if isinstance(role, CommercialRole) else CommercialRole(role)

            if role_enum == CommercialRole.HATE_MAGNET:
                # 悪役は初期は強いが、後半で崩壊する
                if story_progress < 0.3:
                    new_power = min(100.0, new_power + 5)  # 序盤は支配的
                    events.append("establish_dominance")
                    shift_type = "ascending"
                elif story_progress > 0.7:
                    new_power = max(0.0, new_power - 15)  # 終盤で崩壊
                    events.append("dominance_collapse")
                    shift_type = "collapsing"

            elif role_enum == CommercialRole.GROWTH_INVESTMENT:
                # 成長投資：物語進行に応じて自動的に上昇
                for phase in GROWTH_INVESTMENT_PHASES:
                    threshold = phase["threshold"] / 100.0
                    if story_progress >= threshold:
                        phase_power = {
                            1: 20,  # 軽蔑段階
                            2: 40,  # 認識段階
                            3: 70,  # 評価段階
                            4: 95,  # 崇拝段階
                        }.get(phase["phase"], current_power)
                        if phase_power > new_power:
                            new_power = phase_power
                            events.append(f"growth_phase_{phase['phase']}")
                            shift_type = "ascending"

            elif role_enum == CommercialRole.STATUS_FLIP_TRIGGER:
                # 地位逆転トリガー
                if flip_timing_config is None:
                    flip_timing_config = {"story_position_percent": 50, "reversal_intensity": 7}

                flip_position = flip_timing_config.get("story_position_percent", 50) / 100.0
                intensity = flip_timing_config.get("reversal_intensity", 7) / 10.0

                if story_progress >= flip_position:
                    # 逆転発生
                    if current_power < 50:
                        new_power = min(100.0, current_power + (50 * intensity))
                        events.append("status_flip_activated")
                        shift_type = "dramatic_reversal"

            elif role_enum == CommercialRole.UNIQUE_VALUE_PROPOSITION:
                # 希少能力：能力値は高いが承認は徐々に得る
                base_value = 70
                recognition_rate = min(1.0, story_progress * 1.2)
                new_power = base_value + (20 * recognition_rate)
                if recognition_rate > 0.8:
                    events.append("full_recognition_achieved")
                    shift_type = "ascending"

        return (new_power, shift_type, events)


    def analyze_commercial_hegemony_structure(
        characters: Dict[str, Dict],
        story_progress: float = 0.0
    ) -> List[PowerDynamic]:
        """商用役割を考慮した権力構造を分析
        
        Args:
            characters: キャラクター辞書の辞書
                { "character_name": { "type": "...", "commercial_roles": [...], ... } }
            story_progress: 物語の進行度（0.0-1.0）
        
        Returns:
            PowerDynamicオブジェクトリスト
        """
        from config.archetypes import (
            CommercialRole,
            get_status_flip_timing_config,
        )

        power_dynamics = []

        # 主人公を基準にその他のキャラクターとの関係を分析
        protagonist = None
        for name, char_data in characters.items():
            if char_data.get("type") in ("protagonist", "hero", "main_character"):
                protagonist = name
                break

        if not protagonist:
            return power_dynamics

        for name, char_data in characters.items():
            if name == protagonist:
                continue

            char_type = char_data.get("type", "")
            roles = char_data.get("commercial_roles", [])
            power = char_data.get("power_level", 50)

            # 商用役割に応じた初期権力の調整
            for role in roles:
                if role == CommercialRole.HATE_MAGNET:
                    power = min(100.0, power + 20)  # 悪役は初期権力をboost
                elif role == CommercialRole.UNCONDITIONAL_SUPPORTER:
                    power = max(0.0, power - 10)  # サポーターは立場を低く

            # 商用役割による権力変動を適用
            flip_config = None
            if CommercialRole.STATUS_FLIP_TRIGGER in roles:
                flip_config = get_status_flip_timing_config(
                    char_data.get("flip_timing", "mid_flip")
                )

            adjusted_power, shift_type, _ = role_based_power_shift(
                roles, power, story_progress, flip_config
            )

            # PowerDynamicを生成
            hierarchy_level = 3 if adjusted_power > 70 else (2 if adjusted_power > 40 else 1)
            structural_gap = abs(adjusted_power - characters.get(protagonist, {}).get("power_level", 50))

            # 急所（keystone_vulnerability）を商用役割から自動設定
            keystone = _get_role_keystone_vulnerability(roles)

            dynamic = PowerDynamic(
                dominant_char=name if adjusted_power > 50 else protagonist,
                submissive_char=protagonist if adjusted_power > 50 else name,
                hierarchy_level=hierarchy_level,
                structural_gap=structural_gap,
                internal_fragility=_calculate_role_fragility(roles),
                keystone_vulnerability=keystone
            )
            power_dynamics.append(dynamic)

        return power_dynamics


    def _get_role_keystone_vulnerability(roles: List[str]) -> str:
        """商用役割から急所キーワードを取得"""
        from config.archetypes import CommercialRole

        vulnerability_map = {
            CommercialRole.HATE_MAGNET: "unjust_authority_exposed",
            CommercialRole.AVATAR_OF_DESIRE: "hidden_potential_revealed",
            CommercialRole.UNIQUE_VALUE_PROPOSITION: "rare_ability_duplicated",
            CommercialRole.INFORMATION_HEGEMONY: "secret_knowledge_leaked",
            CommercialRole.GROWTH_INVESTMENT: "growth_stunted",
        }

        for role in roles:
            role_enum = role if isinstance(role, CommercialRole) else CommercialRole(role)
            if role_enum in vulnerability_map:
                return vulnerability_map[role_enum]

        return "generic_weakness"


    def _calculate_role_fragility(roles: List[str]) -> float:
        """商用役割から内面的脆さを計算"""
        from config.archetypes import CommercialRole

        fragility = 0.0

        for role in roles:
            role_enum = role if isinstance(role, CommercialRole) else CommercialRole(role)

            if role_enum == CommercialRole.HATE_MAGNET:
                fragility += 40  # 傲慢さは脆さ
            elif role_enum == CommercialRole.UNIQUE_VALUE_PROPOSITION:
                fragility += 25  # 承認への渇望
            elif role_enum == CommercialRole.STATUS_FLIP_TRIGGER:
                fragility += 30  # 地位への執着
            elif role_enum == CommercialRole.UNCONDITIONAL_SUPPORTER:
                fragility -= 20  # 無条件肯定は安定

        return min(100.0, max(0.0, fragility))

