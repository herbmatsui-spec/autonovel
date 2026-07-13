from typing import Dict, List

from pydantic import BaseModel, Field

from kernels.base import KernelBase, KernelContext
from kernels.connection import ConnectionState
from prompts.dialogue_persona import DIALOGUE_PERSONA


class DialogueConfig(BaseModel):
    """
    キャラクター間の呼称や敬語レベルを定義する。
    """
    honorific_level: str = Field(..., description="formal (敬語), casual (タメ口), mixed (混在)")
    addressing_style: str = Field(..., description="last_name (名字), first_name (名前), nickname (愛称), title (役職/肩書き)")
    suffix: str           # "様", "さん", "くん", "ちゃん", "無し"

class DialogueKernel(KernelBase[ConnectionState, DialogueConfig]):
    """
    関係性数値から具体的なダイアログ設定（呼称・口調）を決定し、
    サブテキストを設計してダイアログを制御するカーネル。
    """

    def __init__(self, kernel_id: str = "dialogue_kernel"):
        super().__init__(kernel_id)
        self.persona = DIALOGUE_PERSONA

    async def execute(self, input_data: ConnectionState, context: KernelContext) -> DialogueConfig:
        """
        感情状態に基づいて最適なダイアログ設定を決定し、
        将来的にサブテキスト設計へと繋げる。
        """
        # 現在はConfigの決定のみを行うが、構造的にサブテキスト設計を挿入可能な状態にする
        config = self.determine_dialogue_config(input_data)
        return config

    def determine_dialogue_config(self, state: ConnectionState) -> DialogueConfig:
        """
        感情状態に基づいて、最適なダイアログ設定を決定する。
        """
        # 親愛度と信頼度の平均をベースに関係性の深さを判定
        intimacy = (state.affection + state.trust) / 2

        # 1. 呼称スタイルの決定
        if intimacy >= 80:
            addressing_style = "nickname"
            suffix = "無し"
        elif intimacy >= 60:
            addressing_style = "first_name"
            suffix = "ちゃん/くん"
        elif intimacy >= 40:
            addressing_style = "last_name"
            suffix = "さん"
        else:
            addressing_style = "title"
            suffix = "様"

        # 2. 敬語レベルの決定 (緊張度と親愛度のバランスで判定)
        if intimacy >= 70 and state.tension < 60:
            honorific_level = "casual"
        elif intimacy <= 30 or state.tension >= 80:
            honorific_level = "formal"
        else:
            honorific_level = "mixed"

        return DialogueConfig(
            honorific_level=honorific_level,
            addressing_style=addressing_style,
            suffix=suffix
        )

    def generate_dialogue_instruction(self, char_a: str, char_b: str, config: DialogueConfig) -> str:
        """
        LLM向けの具体的なダイアログ指示文を生成する。
        """
        style_map = {
            "formal": "極めて礼儀正しく、厳格な敬語を使用してください。",
            "casual": "親密な間柄としてのタメ口、あるいは崩れた口調を使用してください。",
            "mixed": "基本は丁寧ですが、時折親しみのある砕けた表現を混ぜてください。"
        }

        address_map = {
            "nickname": "相手を愛称や特別な呼び方で呼んでください。",
            "first_name": "相手を名前で呼んでください。",
            "last_name": "相手を名字で呼んでください。",
            "title": "相手を役職や肩書き、あるいは様付けで呼んでください。"
        }

        return (
            f"【{char_a}から{char_b}への会話ルール】\n"
            f"■ 口調レベル: {style_map[config.honorific_level]}\n"
            f"■ 呼称スタイル: {address_map[config.addressing_style]} (接尾辞: {config.suffix})\n"
            f"※関係性の変化に伴う「呼び方の変化」は物語上の重要な転換点となるため、厳格に遵守してください。"
        )


# =============================================================================
# ステップ21: Avatar Desire Dialogue Generator (自己投影・願望充足用ダイアログ)
# =============================================================================

AVATAR_DESIRE_DIALOGUE_PATTERNS: Dict[str, List[str]] = {
    # 読者への自己投影を喚起するダイアログパターン
    "ideal_self": [
        "「俺는 {}이기 때문에 반드시 해내야 한다」",
        "「이건 내 {}이기 때문이야。무슨 일이 있어도 포기할 수 없어」",
        "「({}라면) 이 정도는 간단히 해낼 수 있을 텐데」",
    ],
    "wish_fulfillment": [
        "「마침내 {}를 손에 넣었다…！이 감격스런 순간을 믿을 수 없어」",
        "「({})라는 꿈이 현실이 되다니…지금의 나를 볼 수 있다면!」",
        "「{}를 맞이한 나는、지금 세계에서 가장 행복한 인간다」",
    ],
    "heroic_declaration": [
        "「({}를 지키기 위해서라면)、나는 어떤 적이라도 물리친다」",
        "「({})…、걱정하지 마라。내가 반드시 지켜주겠노라」",
        "「({})를 향한 나의 충성심은、영원히 변하지 않을 것이다」",
    ],
    "self_improvement": [
        "「({})…、계속해서 강해지겠노라。이 정도로는 만족할 수 없어」",
        "「오늘의 나는 어제의 나보다 {} 늘었다」",
        "「({})를 얻기 위한 쓈련은、이제 시작에 불과하다」",
    ],
    "triumph_over_situations": [
        "「({})라고？、지금의 나에게는 그런 건 문제가 되지 않아」",
        "「이 정도의苦难은 {}에게는 작은 벽에 불과하다」",
        "「({})라는 시련까지、나를更强하게 만들기 위한 것이다」",
    ],
}


def avatar_desire_dialogue_generator(
    avatar_char: str,
    desire_target: str,
    dialogue_type: str = "ideal_self",
    intensity: float = 1.0,
) -> str:
    """
    AVATAR_OF_DESIRE役キャラクターのダイアログを生成する。
    
    Args:
        avatar_char: アバターキャラクター名
        desire_target: 願望対象（能力・地位・関係性など）
        dialogue_type: ダイアログタイプ (ideal_self/wish_fulfillment/heroic_declaration/self_improvement/triumph_over_situations)
        intensity: 強度係数 (0.0-1.0)
    
    Returns:
        生成されたダイアログ指示文
    """
    import random

    patterns = AVATAR_DESIRE_DIALOGUE_PATTERNS.get(dialogue_type, AVATAR_DESIRE_DIALOGUE_PATTERNS["ideal_self"])
    base_template = random.choice(patterns)

    # 強度に応じた修飾
    if intensity >= 0.8:
        modifier = "决对に"
    elif intensity >= 0.5:
        modifier = " 반드시"
    else:
        modifier = ""

    dialogue = base_template.format(desire_target)
    if modifier:
        dialogue = modifier + dialogue

    return (
        f"【{avatar_char}の自己投影・願望充足ダイアログ】\n"
        f"■ 願望対象: {desire_target}\n"
        f"■ ダイアルblogタイプ: {dialogue_type}\n"
        f"■ 強度: {intensity:.0%}\n"
        f"■ 実際のセリフ: 「{dialogue}」\n"
        f"※ 読者が{avatar_char}に自己投影できるよう、普遍的な欲望に訴える表現を使用してくだざい。"
    )


def generate_avatar_fulfillment_scene(
    avatar_char: str,
    reader_desire: str,
    scene_context: str,
) -> str:
    """
    読者願望充足シーンのダイアログプロンプトを生成する。
    
    Args:
        avatar_char: アバターキャラクター
        reader_desire: 読者が抱く願望（例：「最強」「美しい異性からの承認」「复仇」）
        scene_context: シーンの文脈・状況
    
    Returns:
        願望充足シーン用のダイアログ指示
    """
    return (
        f"【願望充足シーン生成: {avatar_char}】\n"
        f"■ シーン文脈: {scene_context}\n"
        f"■ 読者願望: {reader_desire}\n"
        f"■ 期待されるカタルシス: 読者が{avatar_char}を通じて{reader_desire}を間接的に体験できる演出\n"
        f"■ ダイアログ指示:\n"
        f"  1. {avatar_char}の言動が読者の{reader_desire}願望を直接満たす描写を行う\n"
        f"  2. 読者が{avatar_char}に感情移入しやすいよう、普遍的な価値観を使用\n"
        f"  3. 願望成就の瞬間には强いカタルシス効果を持たせる\n"
        f"  4. 短絡的な満足ではなく、夢をldquo;少しずつrdquo;叶めていく過程を描写し、投資심을育成"
    )

