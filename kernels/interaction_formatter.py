from typing import Any, Dict

from kernels.base import KernelState


class InteractionStateFormatter:
    """
    KernelState（数値ベクトル）を、LLMが理解可能な自然言語の指示に変換する。
    """
    @staticmethod
    def format_for_persona(state: KernelState, persona_type: str = "general") -> str:
        """
        ペルソナ定義に注入するための、現在の力学的な状態記述を生成する。
        """
        descriptions = []

        # ペルソナ別の重点分析
        # ペルソナ別の重点分析
        if persona_type == "hegemony":
            if state.hegemony > 70:
                descriptions.append("【支配的状況】あなたは完全に場を支配しており、相手はあなたの意向に従わざるを得ない状況です。")
            elif state.hegemony < 30:
                descriptions.append("【脆弱な状況】あなたの権威は揺らいでおり、相手に主導権を握られやすい状況です。")
            if state.resonance > 60:
                descriptions.append("【共鳴による軟化】強い共鳴があなたの支配的な壁を溶かし、権威ではなく信頼によるリードを促しています。")
            if state.conflict > 60:
                descriptions.append("【衝突による不安定化】激しい葛藤があなたの支配体制に亀裂を入れ、権威への反発が強まっています。")

        elif persona_type == "conflict":
            if state.conflict > 70:
                descriptions.append("【激しい衝突】価値観の根本的な不一致があり、緊張感が最高潮に達しています。")
            if state.hegemony > 60:
                descriptions.append("【構造的圧力】強固な覇権構造が葛藤を抑圧しており、水面下での激しい心理戦が展開されています。")
            if state.serenity > 60:
                descriptions.append("【静謐による抑制】深い静謐さが衝突の熱量を奪っており、爆発的な衝突よりも静かな断絶が際立っています。")

        elif persona_type == "resonance":
            if state.resonance > 70:
                descriptions.append("【深い共鳴】言葉を超えた相互理解が存在し、精神的な距離が極めて近くなっています。")
            elif state.resonance < 30:
                descriptions.append("【精神的乖離】互いの波長が合わず、本質的な理解が困難な状況です。")
            if state.conflict > 60:
                descriptions.append("【共鳴の中の痛み】深い繋がりがあるからこそ、現在の葛藤が鋭い痛みとして機能しています。")

        else: # general
            if state.hegemony > 70:
                descriptions.append("【支配的状況】場を支配する強い権威が存在します。")
            if state.resonance > 70:
                descriptions.append("【深い共鳴】精神的な同期が極めて高い状態です。")
            if state.conflict > 70:
                descriptions.append("【激しい衝突】緊張感が最高潮に達しています。")
            if state.serenity > 70:
                descriptions.append("【深い静謐】深い安心感と静寂に包まれています。")

        if not descriptions:
            return "【均衡状態】特筆すべき力学的偏りはなく、安定した関係性にあります。"

        return "\n".join(descriptions)

    @staticmethod
    def format_constraints(state: KernelState) -> Dict[str, Any]:
        """
        描写における制約（禁止事項や強調事項）を生成する。
        """
        constraints = {
            "avoid": [],
            "emphasize": [],
            "narrative_logic": []
        }

        # 1. 覇権 vs 共鳴 (支配の質)
        if state.hegemony > 60:
            if state.resonance > 60:
                constraints["emphasize"].append("信頼に基づく指導、静かな合意、精神的な一体感を持つ権威。")
                constraints["narrative_logic"].append("支配的な立場にある者が、共鳴を通じて相手を包容する形式のリードを行う。")
            else:
                constraints["avoid"].append("過度な共感や、支配的な立場を損なうような弱さの露呈。")
                constraints["emphasize"].append("権威によるコントロールと、それに伴う心理的圧力。")
                constraints["narrative_logic"].append("権力勾配を明確にし、相手に心理的な負荷をかける。")

        # 2. 葛藤 vs 静謐 (緊張の質)
        if state.conflict > 60:
            if state.serenity > 60:
                constraints["emphasize"].append("冷徹な対立、静かな拒絶、表面的な平穏の下に潜む深い断絶。")
                constraints["narrative_logic"].append("激しい感情の爆発ではなく、静寂の中で研ぎ澄まされた緊張感を描写する。")
            else:
                constraints["avoid"].append("唐突な妥協や、根拠のない急激な親密化。")
                constraints["emphasize"].append("価値観のぶつかり合い、拭えない違和感。")
                constraints["narrative_logic"].append("感情的な摩擦を前面に出し、衝突による変化を促す。")

        # 3. 共鳴 vs 葛藤 (痛みの質)
        if state.resonance > 60 and state.conflict > 60:
            constraints["emphasize"].append("親密さゆえの鋭い痛み、裏切りの衝撃、理解し合っているからこそ譲れない絶望。")
            constraints["narrative_logic"].append("精神的な近さと価値観の乖離の矛盾を、心理的な葛藤として描写する。")

        # 4. 静謐の絶対的優位 (リセット状態)
        if state.serenity > 80:
            constraints["avoid"].append("急激な感情の変化や、物語を無理に動かそうとする強引な展開。")
            constraints["emphasize"].append("時間の停滞感、感覚的な充足、精神的な安寧。")
            constraints["narrative_logic"].append("あらゆる力学的な緊張を一時的に解除し、キャラクターに精神的な休息を与える。")

        return constraints

