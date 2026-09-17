"""伏線回収の因果律・整合性チェッカー (v5.0 Relational Memory)

伏線の設置/回収順序の矛盾や、長期放置された伏線の警告を
0ms（純粋ロジック）で生成する静的解析オーディター。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ForeshadowingAuditResult:
    """伏線監査結果"""
    is_valid: bool = True
    order_violations: list[str] = field(default_factory=list)
    stale_warnings: list[str] = field(default_factory=list)
    summary: str = ""

    @property
    def total_issues(self) -> int:
        return len(self.order_violations) + len(self.stale_warnings)


def validate_foreshadowing_order(planted_ep: int, resolved_ep: int) -> bool:
    """伏線設置話数 <= 回収話数 であることを検証する。

    Args:
        planted_ep: 伏線を設置した話数
        resolved_ep: 伏線が回収された話数

    Returns:
        True: 正常な順序, False: 順序矛盾（回収が設置より前）
    """
    return planted_ep <= resolved_ep


def audit_foreshadowings(
    foreshadowings: list[Any],
    current_episode: int,
    stale_threshold: int = 15,
) -> ForeshadowingAuditResult:
    """伏線一覧に対して因果律・整合性の全面チェックを実行する。

    Args:
        foreshadowings: ForeshadowingModel or dict のリスト
        current_episode: 現在の話数
        stale_threshold: この話数以上放置された伏線を警告する閾値

    Returns:
        ForeshadowingAuditResult
    """
    result = ForeshadowingAuditResult()

    for f in foreshadowings:
        if isinstance(f, dict):
            title = f.get("title", "不明")
            planted_ep = f.get("planted_episode", 0)
            resolved_ep = f.get("resolved_episode")
            status = f.get("status", "planted")
            target_ep = f.get("target_episode")
        else:
            title = getattr(f, "title", "不明")
            planted_ep = getattr(f, "planted_episode", 0)
            resolved_ep = getattr(f, "resolved_episode", None)
            status = getattr(f, "status", "planted")
            target_ep = getattr(f, "target_episode", None)

        # 1. 順序矛盾チェック: 回収が設置より前に行われていないか
        if resolved_ep is not None and not validate_foreshadowing_order(planted_ep, resolved_ep):
            result.is_valid = False
            result.order_violations.append(
                f"【順序矛盾】伏線「{title}」: 設置=第{planted_ep}話 だが "
                f"回収=第{resolved_ep}話 (設置前に回収されている)"
            )

        # 2. 長期放置チェック: 未回収のまま stale_threshold 話以上経過
        if status in ("planted", "progressed") and resolved_ep is None:
            age = current_episode - planted_ep
            if age >= stale_threshold:
                result.stale_warnings.append(
                    f"【長期未回収】伏線「{title}」: 設置=第{planted_ep}話, "
                    f"経過={age}話 (閾値: {stale_threshold}話)"
                )

        # 3. 期限超過チェック: target_episode を超えているのに未回収
        if target_ep is not None and status in ("planted", "progressed"):
            if current_episode > target_ep:
                overdue = current_episode - target_ep
                result.stale_warnings.append(
                    f"【期限超過】伏線「{title}」: 回収目標=第{target_ep}話, "
                    f"現在=第{current_episode}話 ({overdue}話超過)"
                )

    if result.order_violations:
        result.is_valid = False

    # サマリー生成
    if result.total_issues == 0:
        result.summary = "伏線の因果律・整合性に問題はありません。"
    else:
        parts = []
        if result.order_violations:
            parts.append(f"順序矛盾: {len(result.order_violations)}件")
        if result.stale_warnings:
            parts.append(f"警告: {len(result.stale_warnings)}件")
        result.summary = f"伏線監査: {', '.join(parts)}"

    return result
