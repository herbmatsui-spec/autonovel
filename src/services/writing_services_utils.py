from typing import Any


def select_best_episode(
    chapters: list[dict[str, Any]], key: str = "audit_score"
) -> dict[str, Any] | None:
    """
    複数の生成エピソードから、指定されたスコアキーが最も高いものを1つ選択して返す。

    Args:
        chapters: エピソードデータのリスト。各要素は dict 形式でスコアを含む想定。
        key: 比較に使用するスコアキー (デフォルト: 'audit_score')

    Returns:
        最高スコアを持つエピソード。リストが空の場合は None を返す。
    """
    if not chapters:
        return None

    # スコアが欠落している場合は 0 として扱う
    return max(chapters, key=lambda x: x.get(key, 0))
