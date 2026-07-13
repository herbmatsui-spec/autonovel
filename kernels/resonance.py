from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from kernels.base import KernelBase, KernelContext
from kernels.connection import ConnectionState


class ResonanceType(Enum):
    SUDDEN_BOND = "sudden_bond"      # 急激な絆の深化（告白、共闘など）
    BREAKUP = "breakup"              # 関係の破綻（決別、裏切りなど）
    TENSION_EXPLOSION = "explosion"   # 緊張の爆発（激しい衝突、情熱的なぶつかり合い）
    TRUST_ANCHOR = "trust_anchor"    # 絶対的信頼の確立（究極の献身など）
    PSYCHOLOGICAL_SYNC = "sync"      # 心理的同期（言葉なき理解、呼吸の同調）

class ResonanceEvent(BaseModel):
    event_type: ResonanceType
    trigger_condition: str
    plot_impact: str
    suggested_scenes: List[str]
    resonance_level_gain: int = 1 # 同期レベルの上昇量

class ResonanceKernel(KernelBase[ConnectionState, Optional[ResonanceEvent]]):
    """
    感情状態の閾値判定を行い、プロット上の転換点（共鳴イベント）をトリガーするカーネル。
    単なる数値的閾値だけでなく、心理的な「同期」を設計する。
    """
    def __init__(self, kernel_id: str = "resonance_kernel"):
        super().__init__(kernel_id)
        self.state_value = 0.0 # Interaction Matrix用

    # (Removed duplicate __init__ above)

    # 共鳴イベントの閾値定義
    THRESHOLDS = {
        ResonanceType.SUDDEN_BOND: {
            "affection": 85,
            "trust": 70,
            "description": "互いの親愛と信頼が極めて高い状態で共鳴した"
        },
        ResonanceType.BREAKUP: {
            "affection": 20,
            "trust": 20,
            "description": "互いの親愛と信頼が底をつき、修復不可能な状態になった"
        },
        ResonanceType.TENSION_EXPLOSION: {
            "tension": 90,
            "description": "心理的な緊張が限界点に達し、何らかの形で爆発するタイミング"
        },
        ResonanceType.TRUST_ANCHOR: {
            "trust": 95,
            "dependence": 70,
            "description": "絶対的な信頼と精神的な依存が結びつき、不可分な関係となった"
        },
        ResonanceType.PSYCHOLOGICAL_SYNC: {
            "trust": 80,
            "affection": 80,
            "description": "高い信頼と親愛に基づき、意識せずとも思考や感情が同期し始めた"
        }
    }

    async def execute(self, input_data: ConnectionState, context: KernelContext) -> Optional[ResonanceEvent]:
        """
        現在の感情状態をチェックし、トリガーされるべき共鳴イベントを返す。
        """
        return self.check_resonance(input_data)

    def check_resonance(self, state: ConnectionState) -> Optional[ResonanceEvent]:
        """
        現在の感情状態をチェックし、トリガーされるべき共鳴イベントを返す。
        """
        # 優先度の高い順にチェック

        # 1. 緊張の爆発 (TENSION_EXPLOSION)
        if state.tension >= self.THRESHOLDS[ResonanceType.TENSION_EXPLOSION]["tension"]:
            return ResonanceEvent(
                event_type=ResonanceType.TENSION_EXPLOSION,
                trigger_condition=self.THRESHOLDS[ResonanceType.TENSION_EXPLOSION]["description"],
                plot_impact="物語の停滞を打破する激しい感情的衝突、または情熱的な展開への転換",
                suggested_scenes=["激しい口論", "衝動的な告白", "身体的な衝突/接触"]
            )

        # 2. 心理的同期 (PSYCHOLOGICAL_SYNC) - 新設: 緩やかながらに深い同期
        if state.trust >= self.THRESHOLDS[ResonanceType.PSYCHOLOGICAL_SYNC]["trust"] and \
           state.affection >= self.THRESHOLDS[ResonanceType.PSYCHOLOGICAL_SYNC]["affection"]:
            return ResonanceEvent(
                event_type=ResonanceType.PSYCHOLOGICAL_SYNC,
                trigger_condition=self.THRESHOLDS[ResonanceType.PSYCHOLOGICAL_SYNC]["description"],
                plot_impact="『言葉を必要としない理解』の成立。二人の間に独自の精神的領域が構築される",
                suggested_scenes=["同時に同じことを口にする", "視線一つで意図を完璧に汲み取る", "静寂が心地よい共有時間となる"],
                resonance_level_gain=1
            )

        # 3. 急激な絆の深化 (SUDDEN_BOND)
        if state.affection >= self.THRESHOLDS[ResonanceType.SUDDEN_BOND]["affection"] and \
           state.trust >= self.THRESHOLDS[ResonanceType.SUDDEN_BOND]["trust"]:
            return ResonanceEvent(
                event_type=ResonanceType.SUDDEN_BOND,
                trigger_condition=self.THRESHOLDS[ResonanceType.SUDDEN_BOND]["description"],
                plot_impact="関係性のステージが一段階上がり、共犯関係や恋人関係への移行",
                suggested_scenes=["深い秘密の共有", "運命的な共闘", "精神的な結合"],
                resonance_level_gain=2
            )

        # 4. 関係の破綻 (BREAKUP)
        if state.affection <= self.THRESHOLDS[ResonanceType.BREAKUP]["affection"] and \
           state.trust <= self.THRESHOLDS[ResonanceType.BREAKUP]["trust"]:
            return ResonanceEvent(
                event_type=ResonanceType.BREAKUP,
                trigger_condition=self.THRESHOLDS[ResonanceType.BREAKUP]["description"],
                plot_impact="これまでの関係性の完全な拒絶、あるいは絶望的な断絶",
                suggested_scenes=["決別宣言", "決定的な裏切り", "冷徹な突き放し"]
            )

        # 5. 絶対的信頼の確立 (TRUST_ANCHOR)
        if state.trust >= self.THRESHOLDS[ResonanceType.TRUST_ANCHOR]["trust"] and \
           state.dependence >= self.THRESHOLDS[ResonanceType.TRUST_ANCHOR]["dependence"]:
            return ResonanceEvent(
                event_type=ResonanceType.TRUST_ANCHOR,
                trigger_condition=self.THRESHOLDS[ResonanceType.TRUST_ANCHOR]["description"],
                plot_impact="相互依存的な強固な絆の確立。物語の精神的支柱となる関係への進化",
                suggested_scenes=["命を預け合う誓い", "絶望の中での唯一の救いとしての再認"],
                resonance_level_gain=2
            )

        return None

    def generate_plot_injection_prompt(self, char_a: str, char_b: str, event: ResonanceEvent) -> str:
        """
        プロットエンジンへ注入するための共鳴イベント指示文を生成する。
        """
        # イベントタイプに応じた詳細な指示の出し分け
        detail_instruction = ""
        if event.event_type == ResonanceType.PSYCHOLOGICAL_SYNC:
            detail_instruction = (
                "特に『同期（Synchronization）』の描写に注力してください。互いの呼吸、視線の動き、"
                "思考のタイミングが重なる「シンクロニシティ」を具体的に描写し、言葉以上の結びつきを表現してください。"
            )
        elif event.event_type == ResonanceType.TENSION_EXPLOSION:
            detail_instruction = "溜め込まれた緊張が一点で爆発するカタルシスを描いてください。"

        return (
            f"【🚨 関係性共鳴イベント発生: {event.event_type.name}】\n"
            f"トリガー条件: {event.trigger_condition}\n"
            f"プロットへの影響: {event.plot_impact}\n"
            f"推奨される展開: {', '.join(event.suggested_scenes)}\n"
            f"指示: 現在のシーン、あるいは直後のシーンにおいて、この感情的爆発を物語の転換点として明確に描写してください。\n"
            f"{detail_instruction}\n"
            f"単なる会話ではなく、物語の構造を揺るがすイベントとして扱ってください。"
        )


# ==========================================
# 商用役割：運命的な結びつきビルダー（ステップ15）
# ==========================================

DESTINED_RESONANCE_SCENES = {
    "first_meeting": {
        "description": "運命的な初対面の演出",
        "elements": [
            "視線が交わった瞬間、世界から音が消えたような感覚",
            "理由はわからないが、胸がざわめく",
            "まるで古い友人か、それ以上の何かかに会ったような既視感",
        ],
        "intensity": 90,
    },
    "soul_recognition": {
        "description": "魂レベルでの相互認識",
        "elements": [
            "互いの瞳の奥に潜む傷または光が同じ形をしている",
            "言葉がなくても相手の考えが伝わる",
            "引き合う力と反発する力が同時に存在する",
        ],
        "intensity": 85,
    },
    "fated_duel": {
        "description": "宿命的な対決・共闘",
        "elements": [
            "何度も交手し、互いを認め合うライバル関係",
            "危機の中で自然と背中を預け合う",
            "手を組まざるを得ない状況の繰り返し",
        ],
        "intensity": 80,
    },
    "mutual_healing": {
        "description": "互いの傷を癒す存在",
        "elements": [
            "相手の前でだけ崩れる強がり",
            "言葉がなくても理解できる沈黙",
            "その存在がいないと世界が色を失う",
        ],
        "intensity": 95,
    },
}


def destined_connection_builder(
    char_a: str,
    char_b: str,
    resonance_pattern: str = "mutual_healing",
    current_scene_context: str = ""
) -> Dict[str, Any]:
    """運命的な結びつきを持つキャラクター間の関係を構築する
    
    Args:
        char_a: 運命的な結びつきを持つキャラクター1
        char_b: 運命的な結びつきを持つキャラクター2
        resonance_pattern: 結びつきのパターン（first_meeting, soul_recognition, fated_duel, mutual_healing）
        current_scene_context: 現在のシーン文脈
    
    Returns:
        運命共鳴イベントデータ辞書
    """
    from config.archetypes import DESTINED_RESONANCE_PATTERNS

    if resonance_pattern not in DESTINED_RESONANCE_SCENES:
        resonance_pattern = "mutual_healing"

    scene_data = DESTINED_RESONANCE_SCENES[resonance_pattern]

    # プロット指示文を生成
    plot_instruction = _generate_destined_plot_instruction(
        char_a, char_b, resonance_pattern, scene_data
    )

    return {
        "connection_type": "destined_resonance",
        "characters": (char_a, char_b),
        "pattern": resonance_pattern,
        "pattern_description": DESTINED_RESONANCE_PATTERNS.get(
            resonance_pattern,
            "互いを補完し合う運命的な結びつき"
        ),
        "scene_elements": scene_data["elements"],
        "intensity": scene_data["intensity"],
        "plot_instruction": plot_instruction,
        "bond_deepening_triggers": _get_bond_deepening_triggers(resonance_pattern),
    }


def _generate_destined_plot_instruction(
    char_a: str,
    char_b: str,
    pattern: str,
    scene_data: Dict
) -> str:
    """運命共鳴シーンのプロット指示文を生成"""
    element_list = "\n".join([f"  - {elem}" for elem in scene_data["elements"]])

    template = f"""
【運命的な結びつきイベント】

■ キャラクター: {char_a} × {char_b}
■ パターン: {scene_data["description"]}
■ 強度: {scene_data["intensity"]}%

■ 描写すべき要素:
{element_list}

■ 指示:
この2人の関係は単なる友人・恋人・ライバルを超えた「運命的な結びつき」です。
以下の点を意識してください：

1. 【必然性の演出】この2人が出会うことは避けられない。どんな状況でも自然に引き寄せられる。
2. 【魂の共振】言葉にしなくても互いの感情・考えが伝わる瞬間を描写する。
3. 【独立的価値】それぞれのキャラクターが「この人だから」という理由を明確に持つ。
4. 【深化の契機】何かの危機や共通の目標がなくても、自然と絆が深まる機会を作る。

現在シーン: {current_scene_context or "（指定なし）"}
"""
    return template


def _get_bond_deepening_triggers(pattern: str) -> List[str]:
    """結びつきを深めるトリガー条件を返す"""
    base_triggers = [
        "一方が危機に陥った时的另一方の自然な介入学",
        "长期间の别れ後の再会時の感情の爆発",
        "互いの秘密を共有する瞬間の信頼の昇華",
    ]

    pattern_triggers = {
        "first_meeting": [
            "二度目の偶遇での更なる運命の強まり",
            "离ればなれでも忘れられない存在感",
        ],
        "soul_recognition": [
            "互いの隠された伤を知った时的深い理解",
            "同样的痛みを持つ者同士の连帯感",
        ],
        "fated_duel": [
            "互いを上回る وتطويرし合う競争",
            "最强の敌かつ最强の友という矛盾の受容",
        ],
        "mutual_healing": [
            "，对方面前でのみ見せる弱さの共有",
            "治愈には欠落部分への共同的挑戦が必要",
        ],
    }

    return base_triggers + pattern_triggers.get(pattern, [])


def is_destined_connection(char_a: str, char_b: str, characters: Dict) -> bool:
    """2キャラクターが運命的な結びつきを持つかチェック
    
    Args:
        char_a: キャラクター名A
        char_b: キャラクター名B
        characters: 全キャラクター辞書
    
    Returns:
        運命的な結びつきを持つか
    """
    from config.archetypes import CommercialRole

    char_a_data = characters.get(char_a, {})
    char_b_data = characters.get(char_b, {})

    roles_a = char_a_data.get("commercial_roles", [])
    roles_b = char_b_data.get("commercial_roles", [])

    # 少なくとも片方がDESTINED_RESONANCE役割を持つ
    has_destined_a = CommercialRole.DESTINED_RESONANCE in roles_a
    has_destined_b = CommercialRole.DESTINED_RESONANCE in roles_b

    # お互いがresonance_targetsに登録されているか
    resonance_targets_a = char_a_data.get("resonance_targets", [])
    resonance_targets_b = char_b_data.get("resonance_targets", [])

    is_targeted_a = char_b in resonance_targets_a
    is_targeted_b = char_a in resonance_targets_b

    return (has_destined_a or has_destined_b) and (is_targeted_a or is_targeted_b)

