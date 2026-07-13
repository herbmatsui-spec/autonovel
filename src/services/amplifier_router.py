from enum import Enum
from typing import Any, Dict


class AmplifierType(str, Enum):
    COMBAT      = "combat"       # 戦闘・魔法・物理
    PSYCHOLOGY  = "psychology"   # ヘイト・内面葛藤・屈辱
    SCENERY     = "scenery"      # 情景・飯テロ・日常
    CATHARSIS   = "catharsis"    # カタルシス・逆転・圧倒
    NONE        = "none"         # 汎用（fallback）

# catharsis_type -> AmplifierType 判定キーワード
_CATHARSIS_TYPE_MAP = {
    AmplifierType.COMBAT:      ["戦闘", "battle", "fight", "魔法", "物理", "power", "overwhelming"],
    AmplifierType.PSYCHOLOGY:  ["傲慢", "屈服", "崩壊", "collapse", "humiliation", "精神的", "psychological", "内的", "葛藤"],
    AmplifierType.SCENERY:     ["日常", "スローライフ", "飯テロ", "食事", "環境", "生活", "fulfillment"],
    AmplifierType.CATHARSIS:   ["逆転", "reversal", "ざまぁ", "断罪", "報復", "retribution", "status"],
}

# beat_type -> AmplifierType 優先マップ
_BEAT_TYPE_MAP = {
    "具体的行動": AmplifierType.COMBAT,
    "内面葛藤":   AmplifierType.PSYCHOLOGY,
    "状況":       AmplifierType.SCENERY,
    "余韻":       AmplifierType.SCENERY,
    "結末":       AmplifierType.CATHARSIS,
    "展開":       AmplifierType.NONE,
    "導入":       AmplifierType.NONE,
}

PERSONA_MAP = {
    AmplifierType.COMBAT: "[戦闘描写家]",
    AmplifierType.PSYCHOLOGY: "[心理カウンセラー]",
    AmplifierType.SCENERY: "[情景描写家]",
    AmplifierType.CATHARSIS: "[カタルシス演出家]",
    AmplifierType.NONE: "[汎用推敲者]",
}

def detect_amplifier_type(
    beat_type: str = "導入",
    action_description: str = "",
    is_catharsis: bool = False,
    catharsis_type: str = "なし",
) -> AmplifierType:
    """
    beat_type や action_description, is_catharsis などのメタ情報から最適な AmplifierType を判定する。
    """
    if is_catharsis or beat_type == "結末":
        return AmplifierType.CATHARSIS

    # 1. beat_type からの判定
    mapped_type = _BEAT_TYPE_MAP.get(beat_type, AmplifierType.NONE)
    if mapped_type != AmplifierType.NONE:
        return mapped_type

    # 2. action_description 内のキーワード検索による判定
    desc_lower = action_description.lower()
    for amp_type, keywords in _CATHARSIS_TYPE_MAP.items():
        if any(kw in desc_lower for kw in keywords):
            return amp_type

    # 3. catharsis_type キーワードとの照合
    cat_lower = catharsis_type.lower()
    for amp_type, keywords in _CATHARSIS_TYPE_MAP.items():
        if any(kw in cat_lower for kw in keywords):
            return amp_type

    return AmplifierType.NONE

def get_episode_dominant_amplifier(plot_data: Dict[str, Any]) -> AmplifierType:
    """
    エピソード全体の設定から代表的なAmplifierTypeを判定する。
    ビート分解がスキップされた場合のフォールバックなどで利用。
    """
    if plot_data.get("is_catharsis", False):
        return detect_amplifier_type(
            beat_type="結末",
            action_description="",
            is_catharsis=True,
            catharsis_type=plot_data.get("catharsis_type", "なし")
        )

    phase = plot_data.get("current_chain_phase", "")
    if phase in ["Hate", "Defeat", "Conflict"]:
        return AmplifierType.PSYCHOLOGY
    elif phase == "Payoff":
        return AmplifierType.CATHARSIS

    scenes = plot_data.get("scenes", [])
    max_impact = 0
    dominant_desc = ""
    for s in scenes:
        impact = s.get("impact_score", 50)
        if impact > max_impact:
            max_impact = impact
            dominant_desc = s.get("action", "")

    if max_impact >= 70 and dominant_desc:
        return detect_amplifier_type(
            beat_type="展開",
            action_description=dominant_desc,
            is_catharsis=False
        )

    return AmplifierType.NONE
