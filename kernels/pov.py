from dataclasses import dataclass
from typing import Dict


@dataclass
class POVConfig:
    """
    視点（POV）の制御設定を定義する。
    """
    focus_character: str           # 現在の主視点キャラクター
    pov_intensity: str             # "objective" (客観的), "subjective" (主観的), "immersive" (没入的)
    resonance_level: float         # 相手との共鳴度 (0.0 - 1.0)
    pov_switch_frequency: str      # "low" (固定), "mid" (緩やかな切り替え), "high" (頻繁な共鳴的切り替え)

class POVManager:
    """
    絆の深さに応じて、描写の視点（POV）と没入度を最適化するマネージャー。
    """

    def determine_pov_config(self, char_a: str, char_b: str, state: 'ConnectionState') -> POVConfig:
        """
        二人の関係性に基づき、最適なPOV設定を決定する。
        """
        # 親愛度と信頼度の合計を共鳴度として算出
        resonance = (state.affection + state.trust) / 200.0

        # 1. POV強度の決定
        if resonance >= 0.8:
            intensity = "immersive" # 境界が曖昧になるほどの没入感
        elif resonance >= 0.5:
            intensity = "subjective" # 強い主観的な色彩
        else:
            intensity = "objective"  # 距離感のある客観的な描写

        # 2. 視点切り替え頻度の決定
        if resonance >= 0.8:
            frequency = "high" # 互いの感情が共鳴し、視点が頻繁に入れ替わる
        elif resonance >= 0.4:
            frequency = "mid"  # 重要な局面で視点を切り替える
        else:
            frequency = "low"  # 基本的に一人の視点を維持する

        return POVConfig(
            focus_character=char_a,
            pov_intensity=intensity,
            resonance_level=resonance,
            pov_switch_frequency=frequency
        )

    def generate_pov_instruction(self, config: POVConfig, char_a: str, char_b: str) -> str:
        """
        執筆AIへのPOV制御指示文を生成する。
        """
        intensity_map = {
            "objective": "【視点: 客観的】 状況を冷静に描写し、キャラクターの感情は動作や言葉から間接的に推測させてください。",
            "subjective": f"【視点: {config.focus_character}主観】 {config.focus_character}の視点から世界を描き、内面的な感情を色濃く反映させてください。",
            "immersive": f"【視点: 共鳴的没入】 {config.focus_character}と{char_b}の精神的な境界が薄い状態です。一方の感情が他方に伝播する様子を、共感覚的に描写してください。"
        }

        freq_map = {
            "low": "視点は固定し、一貫したパースペクティブを維持してください。",
            "mid": "物語の感情的なピークに合わせて、適宜視点を切り替えてください。",
            "high": "二人の感情が激しく共鳴しています。短いスパンで視点を往復させ、相互理解の深化を演出してください。"
        }

        return (
            f"{intensity_map[config.pov_intensity]}\n"
            f"視点制御: {freq_map[config.pov_switch_frequency]}\n"
            f"共鳴レベル: {config.resonance_level:.2f} - 互いの魂がどれほど深く結びついているかを地の文のトーンに反映させてください。"
        )


# =============================================================================
# ステップ22: Unique Value POV Generator (希少価値・承認欲求充足用POV)
# =============================================================================

UNIQUE_VALUE_POV_PATTERNS: Dict[str, Dict[str, str]] = {
    # UNIQUE_VALUE_PROPOSITION役キャラクターのPOVパターン
    "recognition_seeking": {
        "pov_style": "承認欲求に駆られる主観的視点",
        "description": "他者の視線・評価を強く意識した過敏な自己認識",
        "internal_monologue": "あの人の視線は…私が気になるのだろうか？それとも私の願望聞きだろうか？",
    },
    "superiority_display": {
        "pov_style": "優越性を誇る objectivityとsubjectivityの交错",
        "description": "自己の優越性を確認しつつ、他者からの羡望を潜在意識で求める視点",
        "internal_monologue": "この者どもが私の実力を理解できるものか。だが…認めてほしいという気持ちも確かにある。",
    },
    "rare_ability": {
        "pov_style": "特別な能力への自覚と孤独感の同居",
        "description": "希少な能力を持つが故の孤立と、その能力を要する者への渇望",
        "internal_monologue": "この力は私以外には使えない。ならば、私の居場所は…？",
    },
    "destined_special": {
        "pov_style": "特別視されることへの喜びと重責",
        "description": "「特別な存在」として遇される事の快楽と、その重荷の同時存在",
        "internal_monologue": "私がこの場所にいるのは必然。ならば、その期待に応えなければ…！",
    },
}


def unique_value_pov_generator(
    character_name: str,
    value_type: str = "recognition_seeking",
    current_situation: str = "public",
) -> str:
    """
    UNIQUE_VALUE_PROPOSITION役キャラクター用のPOVを生成する。
    
    Args:
        character_name: キャラクター名
        value_type: 価値タイプ (recognition_seeking/superiority_display/rare_ability/destined_special)
        current_situation: 現在状況 (public/private/combat/ceremony)
    
    Returns:
        POV指示文
    """
    pattern = UNIQUE_VALUE_POV_PATTERNS.get(
        value_type,
        UNIQUE_VALUE_POV_PATTERNS["recognition_seeking"]
    )

    situation_modifiers = {
        "public": "他者の視線を意識した描写を加える",
        "private": "内に秘めた渇望や不安を露わにする",
        "combat": "自己的能力を誇示する場面に集中させる",
        "ceremony": "授与・認知の瞬間の感情を濃く描写",
    }

    return (
        f"【{character_name}のUnique Value POV】\n"
        f"■ POVスタイル: {pattern['pov_style']}\n"
        f"■ 状況補正: {situation_modifiers.get(current_situation, situation_modifiers['public'])}\n"
        f"■ 説明: {pattern['description']}\n"
        f"■ 内心の独白例: 「{pattern['internal_monologue']}」\n"
        f"※ 読者が{character_name}に特別感を寄せつつも、共感による感情移入も可能にする。"
    )


def generate_value_acknowledgment_pov(
    character_name: str,
    acknowledging_party: str,
    value_type: str,
) -> str:
    """
    価値認知シーン（他者からキャラクターの価値をめられる場面）のPOVを生成。
    
    Args:
        character_name: 価値をめられるキャラクター
        acknowledging_party: 認知を与える側（読者視点を代理する存在）
        value_type: 価値タイプ
    
    Returns:
        価値認知シーン用のPOV指示
    """
    return (
        f"【価値認知シーンPOV: {character_name}】\n"
        f"■ 認知を与える者: {acknowledging_party}\n"
        f"■ 価値タイプ: {value_type}\n"
        f"■ POVポイント:\n"
        f"  1. {character_name}の内面に他者からの認知が波及する様子を描写\n"
        f"  2. 長期にわたって渇望してきた承認が実装する瞬間のカタルシス\n"
        f"  3. 読者もまた{character_name}を通じて承認欲求の充足を間接体験\n"
        f"■ 期待される感情: 満足感・全能感・連帯感"
    )

