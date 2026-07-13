from typing import Any, Dict

from kernels.base import KernelState
from kernels.interaction_trigger import InteractionTrigger, TriggerRegistry
from kernels.resonance import ResonanceEvent, ResonanceType


def trigger_hegemony_collapse_resonance_burst(current: KernelState, next: KernelState) -> bool:
    """
    覇権が急落し、かつ共鳴がある程度高い場合にトリガーされる。
    """
    hegemony_drop = current.hegemony - next.hegemony
    return hegemony_drop > 20.0 and next.resonance > 40.0

async def action_hegemony_collapse_resonance_burst(context: Any, pipeline: Any):
    """
    共鳴イベントを強制的に生成し、物語に劇的な転換をもたらす。
    """
    print("[KIM Trigger] Hegemony Collapse -> Resonance Burst activated!")

    # ResonanceEventを強制的に生成してコンテキストに注入
    event = ResonanceEvent(
        event_type=ResonanceType.SUDDEN_BOND,
        trigger_condition="覇権構造の崩壊に伴う、精神的な急接近",
        plot_impact="支配関係が消滅し、対等または新たな信頼関係への劇的転換",
        suggested_scenes=["崩れ落ちる権威への共感", "仮面を脱ぎ捨てた本音の衝突", "不可避な感情の爆発"],
        resonance_level_gain=3
    )

    # パイプライン経由でイベントを通知（実装はpipeline側の拡張に依存）
    if hasattr(pipeline, 'inject_resonance_event'):
        await pipeline.inject_resonance_event(event, context)
    else:
        # 暫定的にコンテキストのglobal_stateに保存
        context.global_state['forced_resonance_event'] = event

def create_preset_triggers() -> TriggerRegistry:
    registry = TriggerRegistry()

    # 1. 覇権崩壊 -> 共鳴爆発
    registry.register(InteractionTrigger(
        trigger_id="hegemony_collapse_burst",
        name="覇権崩壊による共鳴爆発",
        condition=trigger_hegemony_collapse_resonance_burst,
        action=action_hegemony_collapse_resonance_burst,
        cooldown=5
    ))

    # 2. 葛藤の極致 -> 静謐への転落 (Catastrophic Silence)
    def trigger_conflict_to_silence(current: KernelState, next: KernelState) -> bool:
        return current.conflict > 80 and next.conflict < 30

    async def action_conflict_to_silence(context: Any, pipeline: Any):
        print("[KIM Trigger] Conflict Peak -> Catastrophic Silence activated!")
        context.global_state['forced_mood'] = "heavy_silence"

    registry.register(InteractionTrigger(
        trigger_id="conflict_catastrophic_silence",
        name="絶望的な静寂",
        condition=trigger_conflict_to_silence,
        action=action_conflict_to_silence,
        cooldown=4
    ))

    return registry


# =============================================================================
# ステップ24: Status Flip Trigger Preset (地位反転トリガー)
# =============================================================================

def trigger_status_flip_low_to_high(current: KernelState, next: KernelState) -> bool:
    """
    ステータスが低い状態から高い状態へ反転する条件を監視。
    過去の不遇が現在の成功によって清算される瞬間にトリガー。
    """
    # 現在のhegemonyが低く(next)、それが急上昇する瞬間
    return current.hegemony < 30 and (next.hegemony - current.hegemony) > 25


async def action_status_flip_low_to_high(context: Any, pipeline: Any):
    """
    ステータス反転（低→高）を演出する。
    読者が「，待ってた！」と思う瞬間。
    """
    print("[KIM Trigger] Status Flip (Low->High) activated!")

    # 過去の屈辱的な記憶を唤起
    context.global_state['status_flip_mode'] = "low_to_high"
    context.global_state['forced_mood'] = "triumphant_revelation"
    context.global_state['narrativebeat'] = "過去の雪辱"


def trigger_status_flip_high_to_low(current: KernelState, next: KernelState) -> bool:
    """
    高いステータスから低い状態へ転落する条件を監視。
    傲慢への天罰的な反転。
    """
    return current.hegemony > 70 and (current.hegemony - next.hegemony) > 30


async def action_status_flip_high_to_low(context: Any, pipeline: Any):
    """
    ステータス反転（高→低）を演出する。
    读者が「落ちろ！」と思っている悪役への天罰。
    """
    print("[KIM Trigger] Status Flip (High->Low) activated!")

    context.global_state['status_flip_mode'] = "high_to_low"
    context.global_state['forced_mood'] = "schadenfreude"
    context.global_state['narrativebeat'] = "天罰による降格"


def trigger_status_flip_relationship_reversal(current: KernelState, next: KernelState) -> bool:
    """
    関係性における主従関係が反転する条件を監視。
    例：支配していた側と支配されていた側の関係が逆転
    """
    # 共鳴が急上昇かつ、hegemony差が縮小
    resonance_jump = next.resonance - current.resonance
    hegemony_gap_shrink = abs(100 - current.hegemony) - abs(100 - next.hegemony)
    return resonance_jump > 20 and hegemony_gap_shrink > 15


async def action_status_flip_relationship_reversal(context: Any, pipeline: Any):
    """
    関係性の主従反転を演出する。
    「あの人は私に頭が上がらない)等、身分相差の逆転描写。
    """
    print("[KIM Trigger] Status Flip (Relationship Reversal) activated!")

    context.global_state['status_flip_mode'] = "relationship_reversal"
    context.global_state['forced_mood'] = "power_reversal_revelation"
    context.global_state['narrativebeat'] = "服従の鎖の解除"


STATUS_FLIP_TIMING_CONFIG: Dict[str, Dict[str, Any]] = {
    "early_flip": {
        "description": "物語序盤での反転（ читательの予想を裏切る）",
        "trigger_position": 0.25,  # 物語の25%地点で反転
        "impact_modifier": 1.2,  # 早期反転はインパクト大
    },
    "mid_flip": {
        "description": "物語中盤での反転（ 山場の演出）",
        "trigger_position": 0.5,
        "impact_modifier": 1.5,  # 中盤反転が最大インパクト
    },
    "climax_flip": {
        "description": "最終盤での反転（ 最終決戦の転換点）",
        "trigger_position": 0.85,
        "impact_modifier": 2.0,  # 最大インパクト
    },
    "multiple_flip": {
        "description": "複数回の段階的反復（  роль翻转の積み重ね）",
        "trigger_positions": [0.3, 0.55, 0.8],
        "impact_modifier": 1.0,  # 徐々に高まるタイプ
    },
}


def register_status_flip_triggers(registry: TriggerRegistry) -> None:
    """
    ステータス反転トリガーをレジストリに追加する。
    """
    # 低→高 反転
    registry.register(InteractionTrigger(
        trigger_id="status_flip_low_to_high",
        name="ステータス反転（低→高）",
        condition=trigger_status_flip_low_to_high,
        action=action_status_flip_low_to_high,
        cooldown=10  # 長いクールダウンで何度も触发 방지
    ))

    # 高→低 反転（悪役用）
    registry.register(InteractionTrigger(
        trigger_id="status_flip_high_to_low",
        name="ステータス反転（高→低）",
        condition=trigger_status_flip_high_to_low,
        action=action_status_flip_high_to_low,
        cooldown=8
    ))

    # 関係性反転
    registry.register(InteractionTrigger(
        trigger_id="status_flip_relationship_reversal",
        name="関係性主従反転",
        condition=trigger_status_flip_relationship_reversal,
        action=action_status_flip_relationship_reversal,
        cooldown=6
    ))


def generate_status_flip_scene_prompt(
    flip_type: str,
    character_low: str,
    character_high: str,
    flip_reason: str,
    timing: str = "mid_flip",
) -> str:
    """
    ステータス反転シーンのプロンプトを生成。
    
    Args:
        flip_type: 反転タイプ (low_to_high/high_to_low/relationship_reversal)
        character_low: 低いステータスのキャラクター
        character_high: 高いステータスのキャラクター
        flip_reason: 反転の理由・動機
        timing: 反転のタイミング設定
    
    Returns:
        シーン生成プロンプト
    """
    timing_config = STATUS_FLIP_TIMING_CONFIG.get(timing, STATUS_FLIP_TIMING_CONFIG["mid_flip"])

    flip_narratives = {
        "low_to_high": (
            f"【雪辱シーン】{character_low}はかつて{character_high}に踏みにじられた過去を持つ。\n"
            f"その怨念を胸に、{character_low}は今、確信犯的に{character_high}を跪かせようとしている。\n"
            f"「かつての借り、必ず返让您く」——この瞬間のために待った。"
        ),
        "high_to_low": (
            f"【天罰シーン】{character_high}の付け上がる態度遂に限界へ。\n"
            f"{character_low}或其他の証人が、{character_high}の正体を暴く証拠を突き付ける。\n"
            f"瞬く間に崩れる地位。傲慢だった者は無力な立場へと転落する。"
        ),
        "relationship_reversal": (
            f"【服従解放シーン】{character_low}と{character_high}の関係が反転する。\n"
            f"支配されていた{character_low}が主導権を掌握。\n"
            f"「もう命じないでください、主人様？」——その言葉には甘美な復讐の味が籠もる。"
        ),
    }

    return (
        f"【ステータス反転シーン生成】\n"
        f"■ 反転タイプ: {flip_type}\n"
        f"■ タイミング: {timing_config['description']}\n"
        f"■ 影響係数: {timing_config['impact_modifier']}\n"
        f"■ ナラティブ:\n{flip_narratives.get(flip_type, flip_narratives['low_to_high'])}\n"
        f"■ 反転理由: {flip_reason}\n"
        f"※ ステータス反転は、商業的物語において最も強力なカタルシスポイントの1つです。"
    )

