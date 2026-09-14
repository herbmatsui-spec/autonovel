import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.bible_service import WorldBibleGenerator

def test_bible_service_nested_value():
    generator = WorldBibleGenerator(None, None, None, None, None, None)
    obj = {"world_rules": {"magic": {"cost": "mana"}}}
    val = generator._get_nested_value(obj, "world_rules.magic.cost")
    assert val == "mana"
    
    success = generator._set_nested_value(obj, "world_rules.magic.cost", "stamina")
    assert success is True
    assert obj["world_rules"]["magic"]["cost"] == "stamina"

def test_bible_service_nested_value_invalid_target():
    generator = WorldBibleGenerator(None, None, None, None, None, None)
    obj = {"scalar_field": 123}
    # trying to set a sub-field on a scalar int should fail
    success = generator._set_nested_value(obj, "scalar_field.sub", 456)
    assert success is False
