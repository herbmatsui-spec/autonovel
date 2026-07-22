from src.backend.engine_context import ContextManager

def test_parse_dict():
    """registry_data が dict の場合そのまま返る"""
    class FakeChar:
        name = "太郎"
        registry_data = {"personality": "明るい", "ability": "剣術"}
    result = ContextManager._parse_character_registry(FakeChar())
    assert result == {"personality": "明るい", "ability": "剣術"}

def test_parse_json_string():
    """registry_data が JSON文字列の場合パースされる"""
    class FakeChar:
        name = "花子"
        registry_data = '{"personality": "優しい"}'
    result = ContextManager._parse_character_registry(FakeChar())
    assert result == {"personality": "優しい"}

def test_parse_invalid_json():
    """registry_data が不正な JSON の場合空辞書が返る"""
    class FakeChar:
        name = "壊れたデータ"
        registry_data = "not json"
    result = ContextManager._parse_character_registry(FakeChar())
    assert result == {}

def test_parse_model_dump_fallback():
    """registry_data がなく model_dump() がある場合それが使われる"""
    class FakeChar:
        name = "次郎"
        def model_dump(self):
            return {"personality": "真面目"}
    result = ContextManager._parse_character_registry(FakeChar())
    assert result == {"personality": "真面目"}

def test_parse_to_safe_dict():
    """to_safe_dict() がある場合（CharacterDbModel）それが最優先される"""
    class FakeChar:
        name = "三郎"
        registry_data = '{"personality": "元気"}'
        def to_safe_dict(self):
            return {"personality": "元気", "extra": True}
    result = ContextManager._parse_character_registry(FakeChar())
    assert result == {"personality": "元気", "extra": True}

def test_parse_none_registry():
    """registry_data が None の場合空辞書が返る"""
    class FakeChar:
        name = "空データ"
        registry_data = None
    result = ContextManager._parse_character_registry(FakeChar())
    assert result == {}
