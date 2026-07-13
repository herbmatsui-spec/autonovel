from dataclasses import dataclass
from typing import Dict, List, Tuple

from kernels.base import KernelBase
from prompts.conflict_persona import CONFLICT_PERSONA


@dataclass
class SocialRole:
    """
    社会的役割（外面的な関係性）を定義する。
    """
    role_name: str  # "上司-部下", "教師-生徒", "敵対関係", "他人"
    expected_affection: float  # 期待される親愛度 (0-100)
    expected_trust: float       # 期待される信頼度 (0-100)
    expected_distance: str      # "distant", "standard", "close"

class ConflictKernel(KernelBase):
    """
    外面的な役割と内面的な感情の乖離（ギャップ）を検出し、葛藤を演出するエンジン。
    また、物語の停滞を検知し、価値観の衝突を強制的に発生させて緊張感を高める。
    """

    def __init__(self, **kwargs):
        self.state_value = 0.0 # Interaction Matrix用
        super().__init__(**kwargs)
        self.persona = CONFLICT_PERSONA

    async def execute(self, context):
        if await self.should_intervene(context):
            return await self.generate_conflict_scene(context)
        return None

    async def should_intervene(self, context) -> bool:
        analytics = getattr(context, 'analytics', None)
        if not analytics:
            return False

        tension = getattr(analytics, 'tension', 0)
        tension_delta = getattr(analytics, 'tension_delta', 0)
        is_too_easy = getattr(analytics, 'is_too_easy', False)

        # 1. 緊張度が低すぎる、または停滞している場合（物語の脱力防止）
        if tension < 30 or (tension < 60 and tension_delta <= 0):
            return True

        # 2. AIが「状況が安易に進みすぎている」と判断した場合
        if is_too_easy:
            return True

        # 3. 感情的な乖離（ギャップ）が激しいキャラクターがシーンに存在する場合
        # (この判定はConnectionStateの分析から動的に行う)

        return False

    async def generate_conflict_scene(self, context):
        """
        価値観の衝突を設計し、シーンに緊張感を注入する。
        """
        # 1. 衝突パターンの選択
        pattern = self._select_conflict_pattern(context)

        # 2. 価値観衝突の設計 ( conflict_collision_prompt.j2 )
        # conflict_design = await self.llm.generate(
        #     prompt="prompts/conflict_collision_prompt.j2",
        #     context=context,
        #     pattern=pattern
        # )

        # 3. 緊張感の増幅描写 ( conflict_tension_polish_prompt.j2 )
        # polished_scene = await self.llm.generate(
        #     prompt="prompts/conflict_tension_polish_prompt.j2",
        #     context=context,
        #     design=conflict_design
        # )

        # 4. 監査ループ ( conflict_audit_prompt.j2 )
        # final_scene = await self._run_audit_loop(polished_scene, context)

        # return final_scene
        pass

    def _select_conflict_pattern(self, context) -> dict:
        """
        状況に応じて最適な対立パターンを選択する。
        """
        import json
        try:
            with open("config/data/conflict_patterns.json", "r", encoding="utf-8") as f:
                patterns = json.load(f)

            # 本来は analytics や characters の状態から動的に選択する
            # ここではデモンストレーションとしてランダムまたは優先度の高いものを返す
            return patterns[0]
        except Exception:
            return {"pattern_id": "default", "name": "General Conflict", "tension_impact": "moderate"}

    async def _run_audit_loop(self, scene: str, context, max_retries: int = 2):
        """
        対立の品質を監査し、NGであれば修正を強制する。
        """
        for i in range(max_retries):
            # audit_result = await self.llm.generate(
            #     prompt="prompts/conflict_audit_prompt.j2",
            #     context=context,
            #     scene=scene
            # )
            # if "PASS" in audit_result:
            #     return scene
            # scene = await self.llm.generate(
            #     prompt="修正指示に基づいた再生成",
            #     context=context,
            #     audit_result=audit_result
            # )
            pass
        return scene

    def analyze_gap(self, role: SocialRole, state: 'ConnectionState') -> Dict:
        """
        社会的役割と現在の感情状態の乖離を分析する。
        """
        affection_gap = state.affection - role.expected_affection
        trust_gap = state.trust - role.expected_trust

        gap_intensity = "none"
        if abs(affection_gap) > 30 or abs(trust_gap) > 30:
            gap_intensity = "moderate"
        if abs(affection_gap) > 60 or abs(trust_gap) > 60:
            gap_intensity = "severe"

        return {
            "affection_gap": affection_gap,
            "trust_gap": trust_gap,
            "intensity": gap_intensity,
            "type": self._determine_gap_type(affection_gap, trust_gap)
        }

    def _determine_gap_type(self, aff_gap: float, tru_gap: float) -> str:
        if aff_gap > 30 and tru_gap < -20:
            return "unrequited_longing"
        if aff_gap < -30 and tru_gap > 30:
            return "reluctant_reliance"
        if aff_gap > 30 and tru_gap > 30:
            return "hidden_affection"
        if aff_gap < -30 and tru_gap < -30:
            return "suppressed_hostility"
        return "standard"

    def generate_conflict_prompt(self, char_a: str, char_b: str, role: SocialRole, state: 'ConnectionState') -> str:
        analysis = self.analyze_gap(role, state)
        if analysis["intensity"] == "none":
            return ""

        gap_type = analysis["type"]
        type_desc = {
            "unrequited_longing": "惹かれているが同時に強い不信感を抱いている",
            "reluctant_reliance": "相手を嫌悪しているが、能力や状況的に信頼せざるを得ない",
            "hidden_affection": "社会的な役割の制約により、内面の深い好意を隠している",
            "suppressed_hostility": "外面的な礼儀や役割の下に、激しい憎悪や拒絶を押し殺している",
            "standard": "内面と外面に乖離がある"
        }

        intensity_desc = {
            "moderate": "時折、ふとした瞬間にその矛盾が漏れ出る",
            "severe": "常に激しい葛藤があり、精神的な負荷がかかっている"
        }

        return (
            f"【{char_a}の心理的葛藤（ギャップ）演出】\n"
            f"現在の状況: {role.role_name}としての役割を演じつつ、内面では「{type_desc[gap_type]}」状態にあります。\n"
            f"演出強度: {intensity_desc[analysis['intensity']]}\n"
            f"指示: 表面的には役割に沿った振る舞いをさせつつ、モノローグや微細な表情の変化、あるいは「不自然な言い淀み」を通じて、内面の矛盾を読者に提示してください。"
        )


# ==========================================
# 商用役割：憎悪増幅ループ（ステップ18）
# ==========================================

# 憎悪を蓄積させる行動パターン
HATE_ACCUMULATION_PATTERNS = {
    "arrogant_abuse": {
        "description": "傲慢な権利濫用と弱者への侮辱",
        "examples": [
            "「お前に何ができる？ 控えめに言っても足手まといだ」",
            "「この程度のこともできないのか？ 情けない」",
            "「お前は最初からその程度で良かったのだ」",
        ],
        "accumulation_rate": 15,  # 1回あたりの憎悪蓄積量
        "trigger_keywords": ["馬鹿", "使えない", "消えろ", "足手まとい"],
    },
    "unjust_punishment": {
        "description": "正当性を欠いた理不尽な罰・追放",
        "examples": [
            "証拠もなく「お前が盗んだのだろう」と言って追放する",
            "自分の失敗を「お前のせい」にして恥辱を与える",
            "「お前の価値はこの程度だ」と公然と侮辱する",
        ],
        "accumulation_rate": 25,
        "trigger_keywords": ["追放", "証拠なし", "濡れ衣", "理不尽"],
    },
    "belittling_achievement": {
        "description": "主人公の頑張り・成果を嘲笑・軽視",
        "examples": [
            "「たまたま運が良かっただけだ」",
            "「その程度のことにご丁寧に喜びとは」",
            "「次も成功すると思う？ 甘いよ」",
        ],
        "accumulation_rate": 12,
        "trigger_keywords": ["たまたま", "甘い", "過信", "調子に乗る"],
    },
    "humiliation_public": {
        "description": "公衆の面前での屈辱",
        "examples": [
            "宴会で「お前のために余興を用意した」と言って罰ゲームを実行",
            "「お前の家族にも知らせておこうか？」と脅迫",
            "仲間や恋人の前で「用が済んだら消えろ」と一喝",
        ],
        "accumulation_rate": 20,
        "trigger_keywords": ["面前", "公開", "見せしめ", "辱め"],
    },
}


class HateMagnetState:
    """憎悪集積キャラクターの状態"""
    def __init__(self, character_name: str):
        self.character_name = character_name
        self.hate_accumulated = 0.0  # 0-100
        self.transgressions: List[Dict] = []  # 犯した罪のリスト
        self.audience_anger_level = 0.0  # 読者の怒りレベル

    def add_transgression(self, pattern_key: str, context: str = ""):
        pattern = HATE_ACCUMULATION_PATTERNS.get(pattern_key)
        if pattern:
            self.hate_accumulated = min(100.0, self.hate_accumulated + pattern["accumulation_rate"])
            self.transgressions.append({
                "pattern": pattern_key,
                "description": pattern["description"],
                "context": context,
                "at_time": len(self.transgressions)
            })
            self.audience_anger_level = min(100.0, self.audience_anger_level + pattern["accumulation_rate"] * 0.8)

    def should_trigger_catharsis(self) -> Tuple[bool, float]:
        """カタルシス（報復）トリガー条件をチェック
        
        Returns:
            (トリガーするか, カタルシス強度0-100)
        """
        # 一定以上の憎悪が蓄積되면破裂
        if self.hate_accumulated >= 70:
            return True, self.hate_accumulated

        # 最終盤でなくても、顕著な増加があれば微かな破裂
        if len(self.transgressions) >= 3 and self.hate_accumulated >= 50:
            return True, self.hate_accumulated * 0.7

        return False, 0.0

    def get_catharsis_scene_requirements(self) -> Dict[str, Any]:
        """カタルシス場面に必要な要素を取得"""
        return {
            "intensity": self.audience_anger_level,
            "transgression_count": len(self.transgressions),
            "most_heinous_act": max(
                self.transgressions,
                key=lambda t: HATE_ACCUMULATION_PATTERNS.get(t["pattern"], {}).get("accumulation_rate", 0)
            ) if self.transgressions else None,
            "should_include_elements": [
                "retribution_proportional_to_hate",
                "authority_loss",
                "public_fall_from_grace",
                "protagonist_vindication",
            ]
        }


def hate_amplification_loop(
    hate_magnet_state: HateMagnetState,
    story_progress: float,
    story_arc_type: str = "exile_rise"
) -> Tuple[str, List[str], bool]:
    """憎悪増幅ループを回し、次の憎悪アクションを決定
    
    Args:
        hate_magnet_state: 憎悪集積キャラクターの状態
        story_progress: 物語進行度（0.0-1.0）
        story_arc_type: 物語弧タイプ
    
    Returns:
        (推奨アクションタイプ, 生成されるセリフリスト, カタルシスが発生するか)
    """

    # カタルシス条件をチェック
    trigger_catharsis, catharsis_intensity = hate_magnet_state.should_trigger_catharsis()

    if trigger_catharsis:
        # カタルシス場面を推奨
        return (
            "CATHARSIS_TRIGGER",
            [],
            True
        )

    # まだカタルシスが発生していない場合、憎悪を蓄積するアクションを選択
    # 物語の段階に応じてアクションを選ぶ

    if story_progress < 0.25:
        # 序盤：傲慢な見下し中心
        action_pool = ["arrogant_abuse", "belittling_achievement"]
    elif story_progress < 0.5:
        # 中盤前半：理不尽な罰・追放
        action_pool = ["unjust_punishment", "arrogant_abuse", "humiliation_public"]
    elif story_progress < 0.75:
        # 中盤後半：侮辱と公衆の面前での屈辱
        action_pool = ["humiliation_public", "belittling_achievement", "unjust_punishment"]
    else:
        # 終盤直前：最大の侮辱の連発
        action_pool = ["humiliation_public", "unjust_punishment"]

    # 推奨アクションを選択
    import random
    recommended_action = random.choice(action_pool)
    pattern = HATE_ACCUMULATION_PATTERNS[recommended_action]

    # セリフを生成
    dialogues = pattern["examples"][:2]  # 2つまで

    return (recommended_action, dialogues, False)


def generate_hate_magnet_scene_prompt(
    villain_name: str,
    protagonist_name: str,
    action_type: str,
    context: str = ""
) -> str:
    """憎悪集積キャラクターの場面生成プロンプトを作成"""
    pattern = HATE_ACCUMULATION_PATTERNS.get(action_type, {})
    if not pattern:
        return ""

    return f"""
【憎悪蓄積場面の生成】

■ 悪役: {villain_name}
■ 対象: {protagonist_name}
■ アクションタイプ: {pattern["description"]}

■ 発生するセリフ（例）:
{"".join([f"  - 「{line}」" for line in pattern["examples"]])}

■ 指示:
{pattern["description"]}を描写してください。

要点:
1. {villain_name}の傲慢さと自己陶酔を強調
2. {protagonist_name}の悔しさ・怒りが自然に沸き起こる描写
3. 読者が「絶対に許せない」と思う理不尽さを最大化
4. しかし{villain_name}は自分の非さに気づいていない（または気づいていないふり）

文脈: {context or "（指定なし）"}
"""

