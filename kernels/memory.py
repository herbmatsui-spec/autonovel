from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from kernels.base import KernelBase, KernelContext


class ConnectionMilestone(BaseModel):
    """
    関係性が大きく変動した重要な出来事（絆の履歴）を定義する。
    """
    timestamp: datetime = Field(default_factory=datetime.now)
    event_description: str
    emotional_impact: Dict[str, float]  # {"affection": +10.0, "trust": -5.0, ...}
    context_tags: List[str]            # ["雨の日", "口論", "共闘"]
    importance: float = Field(default=1.0, ge=0.0, le=1.0)            # 重要度

class MemoryKernel(KernelBase[Dict[str, Any], Any]):
    """
    キャラクター間の共有記憶（絆の履歴）を管理するカーネル。
    """

    def __init__(self, kernel_id: str = "memory_kernel"):
        super().__init__(kernel_id)
        # (CharA, CharB) -> List[ConnectionMilestone]
        self.history: Dict[tuple, List[ConnectionMilestone]] = {}

    async def execute(self, input_data: Dict[str, Any], context: KernelContext) -> Any:
        """
        入力データの内容（action）に応じて、記憶の追加または回想を行う。
        """
        action = input_data.get("action")
        if action == "add":
            return self.add_milestone(
                input_data["char_a"], input_data["char_b"],
                input_data["event"], input_data["impact"],
                input_data["tags"], input_data.get("importance", 1.0)
            )
        elif action == "recall":
            return self.generate_recall_prompt(
                input_data["char_a"], input_data["char_b"],
                input_data["current_tags"]
            )
        return None

    def add_milestone(self, char_a: str, char_b: str, event: str, impact: Dict[str, float], tags: List[str], importance: float = 1.0):
        """
        重要な出来事を履歴に追加する。
        """
        pair = tuple(sorted((char_a, char_b)))
        if pair not in self.history:
            self.history[pair] = []

        milestone = ConnectionMilestone(
            timestamp=datetime.now(),
            event_description=event,
            emotional_impact=impact,
            context_tags=tags,
            importance=importance
        )
        self.history[pair].append(milestone)

    def recall_relevant_memories(self, char_a: str, char_b: str, current_tags: List[str], limit: int = 2) -> List[ConnectionMilestone]:
        """
        現在の文脈（タグ）に基づき、関連性の高い過去の記憶を抽出する。
        """
        pair = tuple(sorted((char_a, char_b)))
        if pair not in self.history:
            return []

        memories = self.history[pair]

        # タグの重複度と重要度でスコアリング
        scored_memories = []
        for m in memories:
            score = m.importance
            # タグが一致していればスコア加算
            match_count = len(set(m.context_tags) & set(current_tags))
            score += match_count * 0.5
            scored_memories.append((score, m))

        # スコア順にソートして上位を返す
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [m for score, m in scored_memories[:limit]]

    def generate_recall_prompt(self, char_a: str, char_b: str, current_tags: List[str]) -> str:
        """
        LLMへの指示として、回想すべき記憶をフォーマットして出力する。
        """
        memories = self.recall_relevant_memories(char_a, char_b, current_tags)
        if not memories:
            return ""

        recall_texts = []
        for m in memories:
            recall_texts.append(f"【記憶: {m.event_description}】 (影響: {m.emotional_impact})")

        memories_str = "\n".join(recall_texts)

        return (
            f"【{char_a}と{char_b}の共有記憶（回想トリガー）】\n"
            f"現在の状況に関連し、以下の過去の出来事がキャラクターの意識に浮かんでいます：\n"
            f"{memories_str}\n"
            f"指示: これらの記憶を直接的に記述するのではなく、ふとした瞬間の回想、既視感、あるいは現在の感情を増幅させる根拠として、自然な形で物語に組み込んでください。"
        )


# =============================================================================
# ステップ23: Growth Investment Memory Tracker (成長可視化・投資心理喚起用メモリ)
# =============================================================================

GROWTH_INVESTMENT_MEMORY_TYPES: Dict[str, Dict[str, Any]] = {
    # GROWTH_INVESTMENT役キャラクターの成長記録タイプ
    "power_gain": {
        "description": "力の獲得・成長の記録",
        "memory_template": "【成長記憶】{character}は{previous_level}から{current_level}へと階段を登った。",
        "emotional_hook": "讀者が「この子は大丈夫か？」と心配した先に見える成長の萌芽",
    },
    "skill_acquisition": {
        "description": "スキル・知識の習得記録",
        "memory_template": "【習得記憶】{character}が初めて{skill}を使いこなした日のことは忘れられない。",
        "emotional_hook": "「あの頃是不可能だったこと」が「今」可能になる快楽",
    },
    "relationship_evolution": {
        "description": "人間関係の深化・変化の記録",
        "memory_template": "【関係記憶】{character}と{other}は、{past_state}から{current_state}へと関係を変えた。",
        "emotional_hook": "絆が深まる過程への「親密的投資」の満足感",
    },
    "overcoming_setback": {
        "description": "挫折からの立ち直り記録",
        "memory_template": "【試練記憶】{character}は{setback}という挫折を経て、今は本当に強くなった。",
        "emotional_hook": "「まだこの子は弱小」→「実は隠れた強者」への落差萌え",
    },
    "recognition_achievement": {
        "description": "認知・評価獲得の記録",
        "memory_template": "【認知記憶】{character}が{authority}から「{evaluation}」と認められた日。",
        "emotional_hook": "承認欲求の充足と、読者との共振",
    },
}


class GrowthMilestone:
    """成長投資の軌跡を追跡するクラス"""

    def __init__(self, character_name: str):
        self.character_name = character_name
        self.growth_log: List[Dict[str, Any]] = []
        self.current_power_level: float = 0.0
        self.total_investment_score: float = 0.0

    def record_growth(
        self,
        growth_type: str,
        previous_value: Any,
        current_value: Any,
        context: str = "",
    ) -> None:
        """成長を記録する"""
        growth_entry = {
            "type": growth_type,
            "previous": previous_value,
            "current": current_value,
            "context": context,
        }
        self.growth_log.append(growth_entry)

        # 投資スコアを更新
        self.total_investment_score += 1.0
        # 力と認知度の相関を更新
        if growth_type == "power_gain":
            self.current_power_level = current_value

    def get_investment_return_prompt(self, current_enemy_level: float) -> str:
        """
        現在の投資に対する「見返り」を示すプロンプトを生成する。
        読者が「やっと報われた！」と感じられるポイントを強調。
        """
        recent_growth = self.growth_log[-3:] if len(self.growth_log) >= 3 else self.growth_log

        growth_descriptions = []
        for entry in recent_growth:
            template = GROWTH_INVESTMENT_MEMORY_TYPES.get(
                entry["type"],
                GROWTH_INVESTMENT_MEMORY_TYPES["power_gain"]
            )["memory_template"]
            desc = template.format(
                character=self.character_name,
                previous_level=entry.get("previous", "?"),
                current_level=entry.get("current", "?"),
                skill=entry.get("current", "?"),
                other=entry.get("context", "相手"),
                past_state=entry.get("previous", "?"),
                current_state=entry.get("current", "?"),
                setback=entry.get("previous", "試練"),
                authority="???",
                evaluation="認められた",
            )
            growth_descriptions.append(desc)

        power_comparison = ""
        if self.current_power_level > 0:
            ratio = self.current_power_level / max(current_enemy_level, 1.0)
            if ratio >= 1.5:
                power_comparison = "【完壁な力差】この程度の敵なら、{character}の現在の実力で压倒的に有利"
            elif ratio >= 1.0:
                power_comparison = "【互角以上の戦い】ようやく実力が並び、勝利が見えてきた"
            elif ratio >= 0.7:
                power_comparison = "【善戦！】實は成長の跡が見え、追い上げている"
            else:
                power_comparison = "【苦戦！】しかし、焦げないこと自体が成長の證"

        return (
            f"【{self.character_name}の成長投資リターン】\n"
            f"■ 最近の成長軌跡:\n" + "\n".join(f"  - {d}" for d in growth_descriptions) + "\n"
            f"■ 累積投資スコア: {self.total_investment_score:.0f}\n"
            f"■ 現在の力量レベル: {self.current_power_level:.1f}\n"
            f"■ 戦況分析: {power_comparison.format(character=self.character_name)}\n"
            f"※ 讀者が{self.character_name}に投資してきた時間・感情の、見返りとして機能する場面を描写してください。"
        )


def growth_investment_memory_tracker(
    character_name: str,
    growth_log: List[Dict[str, Any]],
    current_phase: int,
) -> str:
    """
    GROWTH_INVESTMENT役キャラクターの成長記録に基づくメモリプロンプトを生成。
    
    Args:
        character_name: キャラクター名
        growth_log: 成長記録のリスト
        current_phase: 現在の成長段階
    
    Returns:
        成長投資メモリオブジェクトのJSON文字列
    """
    milestone = GrowthMilestone(character_name)

    for entry in growth_log:
        milestone.record_growth(
            growth_type=entry.get("type", "power_gain"),
            previous_value=entry.get("previous"),
            current_value=entry.get("current"),
            context=entry.get("context", ""),
        )

    return milestone.get_investment_return_prompt(current_enemy_level=current_phase * 10)


def generate_investment_return_scene_prompt(
    character_name: str,
    investment_type: str,
    payoff_amount: float,
) -> str:
    """
    投資の「大回収」シーンのプロンプトを生成。
    讀者が「待ってた！」と思う瞬間を描写する指示。
    """
    return (
        f"【投資回収シーン: {character_name}】\n"
        f"■ 投資タイプ: {investment_type}\n"
        f"■ 見返りの大きさ: {payoff_amount:.0%}\n"
        f"■ シーン描写的重点:\n"
        f"  1. 「あの頃の辛苦」が「現在の強さ」として実を結ぶ瞬間\n"
        f"  2. {character_name}が過去の自分を見て感じる矜持と满足\n"
        f"  3. 読者も同じく「成長を見た」という全能感の享受\n"
        f"  4. 「ここで報われた」と感じる山場の感情的な峰值\n"
        f"※ 成長投資型キャラクターにおいては、この瞬間が最大的カタルシスポイントになります。"
    )

