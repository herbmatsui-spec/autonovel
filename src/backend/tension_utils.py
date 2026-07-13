from typing import Optional

from src.backend.tension_curve_config import DEFAULT_CURVE, EMOTIONAL_CURVES, select_curve_by_hook


def select_tension_curve(genre: str, story_type: Optional[str] = None) -> str:
    """
    ジャンルや物語のタイプに基づいて最適な感情曲線を選択する。
    """
    # 特定の物語タイプ（例: ざまぁ）が指定されている場合は優先
    if story_type == "zamaa":
        return "zamaa_heavy"

    # ジャンルに基づく簡易的なマッピング（将来的に拡張可能）
    genre_map = {
        "revenge": "zamaa_heavy",
        "zamaa": "zamaa_heavy",
        "mystery": "slow_burn",
        "romance": "standard",
    }

    return genre_map.get(genre.lower(), DEFAULT_CURVE)

def calculate_progress(current_episode: int, total_episodes: int) -> float:
    """
    現在のエピソード番号から物語の進行度（0.0 〜 1.0）を計算する。
    """
    if total_episodes <= 0:
        return 0.0
    # エピソードの開始時点での進行度を計算
    return (current_episode - 1) / total_episodes

def get_target_tension(curve_name: str, progress: float, hook_name: Optional[str] = None) -> float:
    """
    指定された曲線と進行度から、線形補間を用いて目標Tension値を算出する。

    hook_name が指定されていれば curve_name を上書きする。
    """
    if hook_name is not None:
        curve_name = select_curve_by_hook(hook_name)

    curve = EMOTIONAL_CURVES.get(curve_name, EMOTIONAL_CURVES[DEFAULT_CURVE])

    # 進行度が範囲外の場合のガード
    if progress <= curve[0][0]:
        return curve[0][1]
    if progress >= curve[-1][0]:
        return curve[-1][1]

    # 線形補間
    for i in range(len(curve) - 1):
        p1, t1 = curve[i]
        p2, t2 = curve[i+1]
        if p1 <= progress <= p2:
            # 補間式: t = t1 + (t2 - t1) * (progress - p1) / (p2 - p1)
            return t1 + (t2 - t1) * (progress - p1) / (p2 - p1)

    return curve[-1][1]
