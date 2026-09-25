"""プロットイベント型定義 (Week 2 Step 1)。

プロット上で発生するイベントと、そのイベントにおけるキャラクターの役割を
型安全に扱うためのスキーマ。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class Role(str, Enum):
    """イベント内でのキャラクター役割。

    source (感情を感じる側) / target (感情を向けられる側) の解決に使用する。
    """

    VICTIM = "victim"              # 被害者
    PERPETRATOR = "perpetrator"    # 加害者
    RESCUER = "rescuer"            # 救助者
    WITNESS = "witness"            # 目撃者
    SHARER = "sharer"              # 秘密を共有する側
    RECEIVER = "receiver"          # 秘密を受け取る側
    PARTICIPANT = "participant"    # 参加者
    CONFESSOR = "confessor"        # 告白する側
    LISTENER = "listener"          # 告白を聞く側


class PlotEventType(str, Enum):
    """プロットイベントタイプ。"""

    BETRAYAL = "betrayal"                    # 裏切り
    RESCUE = "rescue"                        # 救出
    CONFESSION = "confession"                # 告白
    COMBAT_VICTORY = "combat_victory"        # 戦闘勝利
    LOSS_OF_LOVED_ONE = "loss_of_loved_one"  # 愛する人の喪失
    SECRET_SHARED = "secret_shared"          # 秘密の共有
    FORCED_COOPERATION = "forced_cooperation"  # 強制協力
    REJECTION = "rejection"                  # 拒絶
    CUSTOM = "custom"                        # カスタムイベント


@dataclass
class PlotEvent:
    """プロットイベント。

    Attributes:
        event_id: 一意なイベントID (例: "ep14_betrayal")
        episode: エピソード番号
        scene: シーン番号 (同一エピソード内の順序)
        event_type: イベントタイプ
        roles: 役割 → キャラクター名のマッピング (例: {"victim": "A"})
        metadata: 任意の追加データ
    """

    event_id: str
    episode: int
    scene: int
    event_type: PlotEventType
    roles: Dict[Role, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.event_type, str):
            self.event_type = PlotEventType(self.event_type)

    def get_character(self, role: Role) -> Optional[str]:
        """指定役割のキャラクター名を取得 (存在しない場合は None)。"""
        if isinstance(role, str):
            role = Role(role)
        return self.roles.get(role)

    def to_dict(self) -> Dict[str, Any]:
        """シリアライズ用辞書変換。"""
        return {
            "event_id": self.event_id,
            "episode": self.episode,
            "scene": self.scene,
            "event_type": self.event_type.value,
            "roles": {role.value if isinstance(role, Role) else role: name
                      for role, name in self.roles.items()},
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PlotEvent:
        """辞書から復元 (YAML パーサ用)。"""
        roles_raw = data.get("roles", {}) or {}
        roles: Dict[Role, str] = {}
        for role_key, name in roles_raw.items():
            try:
                roles[Role(str(role_key).lower())] = str(name)
            except ValueError:
                # 未知の役割は PARTICIPANT にフォールバック
                roles[Role.PARTICIPANT] = str(name)
        return cls(
            event_id=str(data["event_id"]),
            episode=int(data["episode"]),
            scene=int(data.get("scene", 0) or 0),
            event_type=PlotEventType(str(data["event_type"]).lower()),
            roles=roles,
            metadata=dict(data.get("metadata", {}) or {}),
        )


__all__ = ["PlotEvent", "PlotEventType", "Role"]
