"""ForeshadowingStatus Enum定義。

伏線ステートマシンの状態遷移を定義する。
状態遷移: PLANTED → PROGRESSED → RESOLVED
                └→ ABANDONED（回収放棄）
"""
from enum import Enum


class ForeshadowingStatus(str, Enum):
    PLANTED = "planted"        # 伏線設置済み（未回収）
    PROGRESSED = "progressed"  # 進展・匂わせ中
    RESOLVED = "resolved"      # 回収完了
    ABANDONED = "abandoned"    # 回収破棄

    @classmethod
    def active_statuses(cls) -> list["ForeshadowingStatus"]:
        """未回収として扱うステータス一覧を返す"""
        return [cls.PLANTED, cls.PROGRESSED]

    @property
    def is_active(self) -> bool:
        """まだ回収されていない（アクティブ）かどうか"""
        return self in (ForeshadowingStatus.PLANTED, ForeshadowingStatus.PROGRESSED)

    @property
    def is_terminal(self) -> bool:
        """終端状態（RESOLVED or ABANDONED）かどうか"""
        return self in (ForeshadowingStatus.RESOLVED, ForeshadowingStatus.ABANDONED)
