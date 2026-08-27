"""Phase 1 テスト: SceneBase とサブクラスのシリアライズ・ラウンドトリップ検証 (ステップ 15)"""

import pytest
from novel_50ep.scene_model import (
    SceneBase,
    EroticScene,
    DialogueScene,
    CombatScene,
    ExplorationScene,
    make_scene,
)


def test_scene_base_roundtrip():
    s = SceneBase("s1", "generic", 0, 10)
    d = s.to_dict()
    assert d == {"id": "s1", "type": "generic", "start": 0, "end": 10}
    restored = SceneBase.from_dict(d)
    assert restored.id == "s1"
    assert restored.type == "generic"
    assert restored.start == 0
    assert restored.end == 10


def test_erotic_scene_roundtrip():
    s = EroticScene("e1", 0, 10, characters=["凛", "セリア"])
    d = s.to_dict()
    assert d["type"] == "erotic"
    assert d["characters"] == ["凛", "セリア"]
    restored = SceneBase.from_dict(d)
    assert isinstance(restored, EroticScene)
    assert restored.id == "e1"
    assert restored.characters == ["凛", "セリア"]


def test_dialogue_scene_roundtrip():
    s = DialogueScene("d1", 10, 20, speakers=["凛", "ガルド"], utterances=["行くぞ", "了解"], topics=["潜入"])
    d = s.to_dict()
    assert d["type"] == "dialogue"
    assert d["speakers"] == ["凛", "ガルド"]
    assert d["utterances"] == ["行くぞ", "了解"]
    assert d["topics"] == ["潜入"]
    restored = SceneBase.from_dict(d)
    assert isinstance(restored, DialogueScene)
    assert restored.speakers == ["凛", "ガルド"]
    assert restored.topics == ["潜入"]


def test_combat_scene_roundtrip():
    s = CombatScene("c1", 20, 30, hp=100, mp=50, equipment=["光刃", "盾"], enemies=["闇尖兵"])
    d = s.to_dict()
    assert d["type"] == "combat"
    assert d["hp"] == 100
    assert d["mp"] == 50
    assert d["equipment"] == ["光刃", "盾"]
    assert d["enemies"] == ["闇尖兵"]
    restored = SceneBase.from_dict(d)
    assert isinstance(restored, CombatScene)
    assert restored.hp == 100
    assert restored.mp == 50
    assert restored.equipment == ["光刃", "盾"]
    assert restored.enemies == ["闇尖兵"]


def test_exploration_scene_roundtrip():
    s = ExplorationScene("x1", 30, 40, location="蒼穹の回廊", items=["光の鍵"], map_flags={"door_unlocked": True})
    d = s.to_dict()
    assert d["type"] == "exploration"
    assert d["location"] == "蒼穹の回廊"
    assert d["items"] == ["光の鍵"]
    assert d["map_flags"] == {"door_unlocked": True}
    restored = SceneBase.from_dict(d)
    assert isinstance(restored, ExplorationScene)
    assert restored.location == "蒼穹の回廊"
    assert restored.items == ["光の鍵"]
    assert restored.map_flags == {"door_unlocked": True}


def test_make_scene_factory():
    s = make_scene("combat", id="c2", start=0, end=5, hp=80)
    assert isinstance(s, CombatScene)
    assert s.hp == 80
