"""統一シーン基底クラスとシリアライズ (Phase 1 / ステップ 7〜15)"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


class SceneBase:
    """全シーンの基底クラス (ステップ 7, 8, 14)"""

    def __init__(self, id: str, type: str, start: int, end: int, **kwargs: Any):
        self.id = id
        self.type = type
        self.start = start
        self.end = end

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "start": self.start,
            "end": self.end,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SceneBase:
        data = dict(d)
        stype = data.pop("type", "base")
        if stype == "base":
            return cls(**data)
        return make_scene(stype, **data)


class EroticScene(SceneBase):
    """官能シーン (ステップ 9)"""

    def __init__(
        self,
        id: str,
        start: int,
        end: int,
        characters: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        super().__init__(id, "erotic", start, end)
        self.characters = list(characters) if characters is not None else []

    def to_dict(self) -> Dict[str, Any]:
        res = super().to_dict()
        res["characters"] = self.characters
        return res


class DialogueScene(SceneBase):
    """会話シーン (ステップ 10, 37)"""

    def __init__(
        self,
        id: str,
        start: int,
        end: int,
        speakers: Optional[List[str]] = None,
        utterances: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        super().__init__(id, "dialogue", start, end)
        self.speakers = list(speakers) if speakers is not None else []
        self.utterances = list(utterances) if utterances is not None else []
        self.topics = list(topics) if topics is not None else []

    def to_dict(self) -> Dict[str, Any]:
        res = super().to_dict()
        res["speakers"] = self.speakers
        res["utterances"] = self.utterances
        res["topics"] = self.topics
        return res


class CombatScene(SceneBase):
    """戦闘シーン (ステップ 11)"""

    def __init__(
        self,
        id: str,
        start: int,
        end: int,
        hp: int = 0,
        mp: int = 0,
        equipment: Optional[List[str]] = None,
        enemies: Optional[List[str]] = None,
        **kwargs: Any,
    ):
        super().__init__(id, "combat", start, end)
        self.hp = hp
        self.mp = mp
        self.equipment = list(equipment) if equipment is not None else []
        self.enemies = list(enemies) if enemies is not None else []

    def to_dict(self) -> Dict[str, Any]:
        res = super().to_dict()
        res["hp"] = self.hp
        res["mp"] = self.mp
        res["equipment"] = self.equipment
        res["enemies"] = self.enemies
        return res


class ExplorationScene(SceneBase):
    """探索シーン (ステップ 12, 52)"""

    def __init__(
        self,
        id: str,
        start: int,
        end: int,
        location: str = "",
        items: Optional[List[str]] = None,
        map_flags: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        super().__init__(id, "exploration", start, end)
        self.location = location
        self.items = list(items) if items is not None else []
        self.map_flags = dict(map_flags) if map_flags is not None else {}

    def to_dict(self) -> Dict[str, Any]:
        res = super().to_dict()
        res["location"] = self.location
        res["items"] = self.items
        res["map_flags"] = self.map_flags
        return res


def make_scene(type: str, **kw: Any) -> SceneBase:
    """ファクトリ関数 (ステップ 13)"""
    table = {
        "erotic": EroticScene,
        "dialogue": DialogueScene,
        "combat": CombatScene,
        "exploration": ExplorationScene,
    }
    cls = table.get(type)
    if cls is None:
        return SceneBase(type=type, **kw)
    return cls(**kw)
