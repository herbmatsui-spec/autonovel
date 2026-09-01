"""
kernels/pov.py - 視点管理
"""

from enum import Enum


class POVType(Enum):
    FIRST_PERSON = "first_person"
    THIRD_PERSON = "third_person"
    SECOND_PERSON = "second_person"
    OMNISCIENT = "omniscient"
    ALTERNATING = "alternating"


class POVManager:
    """
    視点管理
    """

    def __init__(self):
        self.current_pov: POVType | None = None
        self.available_povs: list[POVType] = [
            POVType.FIRST_PERSON,
            POVType.THIRD_PERSON,
            POVType.OMNISCIENT,
        ]
        self.viewpoint_characters: dict[POVType, list[str]] = {}

    def set_pov(self, pov_type: POVType) -> None:
        """視点を設定"""
        if pov_type in self.available_povs:
            self.current_pov = pov_type

    def add_viewpoint_character(self, pov_type: POVType, character_name: str) -> None:
        """視点キャラクターを追加"""
        if pov_type not in self.viewpoint_characters:
            self.viewpoint_characters[pov_type] = []
        if character_name not in self.viewpoint_characters[pov_type]:
            self.viewpoint_characters[pov_type].append(character_name)

    def get_current_pov(self) -> POVType | None:
        """現在の視点を取得"""
        return self.current_pov

    def get_pov_description(self, pov_type: POVType) -> str:
        """視点の説明を取得"""
        descriptions = {
            POVType.FIRST_PERSON: "第一人称（「私/働く/わたし」）",
            POVType.THIRD_PERSON: "第三人称（「彼/彼女/アンナ」）",
            POVType.SECOND_PERSON: "第二人称（「あなた」）",
            POVType.OMNISCIENT: "全知視点（あらゆる人物の心も知る）",
            POVType.ALTERNATING: "交替視点（複数人の視点を切り替え）",
        }
        return descriptions.get(pov_type, "不明")

    def is_valid_pov(self, pov_type: POVType) -> bool:
        """有効な視点か"""
        return pov_type in self.available_povs

    def reset(self) -> None:
        """リセット"""
        self.current_pov = None
        self.viewpoint_characters.clear()
