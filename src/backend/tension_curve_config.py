from typing import Dict, List, Tuple

# 感情曲線（Tension Curve）の定義
# 各曲線は (進行度, 目標Tension値) のリストで定義される。
# 進行度は 0.0 (開始) から 1.0 (終了) まで。
# Tension値は 0.0 (安寧/日常) から 1.0 (最大緊張/絶望) まで。

EMOTIONAL_CURVES: Dict[str, List[Tuple[float, float]]] = {
    "standard": [
        (0.0, 0.2),  # 導入
        (0.2, 0.4),  # 状況の悪化
        (0.5, 0.7),  # 中盤の山場
        (0.8, 0.9),  # クライマックス直前
        (1.0, 0.1),  # 結末（解消）
    ],
    "zamaa_heavy": [
        (0.0, 0.3),  # 導入
        (0.1, 0.8),  # 急激な絶望（溜めの開始）
        (0.4, 0.9),  # 絶望の底（最大溜め）
        (0.6, 0.7),  # 逆転の兆し
        (0.8, 1.0),  # カタルシス爆発（最大緊張から解放へ）
        (1.0, 0.0),  # 完全な平穏
    ],
    "slow_burn": [
        (0.0, 0.1),  # 静かな始まり
        (0.3, 0.3),  # 緩やかな緊張
        (0.6, 0.6),  # 徐々に高まる
        (0.9, 0.9),  # 終盤の急加速
        (1.0, 0.2),  # 結末
    ],
}

DEFAULT_CURVE = "standard"

HOOK_CURVE_MAP = {
    "catharsis": "zamaa_heavy",
    "empathy_peak": "slow_burn",
    "chilling": "standard",
    "righteous_anger": "standard",
    "triumph": "zamaa_heavy",
    "serenity": "slow_burn",
    "nostalgia": "slow_burn",
    "awe": "standard",
}


def select_curve_by_hook(hook_name: str) -> str:
    """感情起点名から適用するtension曲線名を返す。未知フックは DEFAULT_CURVE。"""
    return HOOK_CURVE_MAP.get(hook_name, DEFAULT_CURVE)

