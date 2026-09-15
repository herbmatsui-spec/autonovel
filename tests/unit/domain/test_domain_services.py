import pytest
from src.domain.entities.character import Character
from src.domain.value_objects.ids import NovelId, CharacterId

def test_character_entity_creation():
    char = Character(
        id=CharacterId.generate(),
        novel_id=NovelId.generate(),
        name="アリス",
        role="protagonist",
        personality="冷徹だが仲間思い"
    )
    assert char.name == "アリス"
    assert char.role == "protagonist"
    assert "冷徹" in char.personality

def test_character_update_personality():
    char = Character(
        id=CharacterId.generate(),
        novel_id=NovelId.generate(),
        name="ボブ",
        role="antagonist",
        personality="傲慢"
    )
    char.personality = "謙虚"
    assert char.personality == "謙虚"