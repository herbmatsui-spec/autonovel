import pytest
from src.services.hook_templates import HOOK_TEMPLATES, get_hook_templates, get_all_hook_types


def test_hook_templates_dict_exists():
    """HOOK_TEMPLATES 辞書が存在することを確認"""
    assert HOOK_TEMPLATES is not None
    assert isinstance(HOOK_TEMPLATES, dict)


def test_hook_templates_has_required_types():
    """必要なフックタイプが含まれていることを確認"""
    assert "mystery" in HOOK_TEMPLATES
    assert "threat" in HOOK_TEMPLATES
    assert "emotion" in HOOK_TEMPLATES


def test_hook_templates_templates_are_lists():
    """各フックタイプのテンプレートがリストであることを確認"""
    for hook_type, templates in HOOK_TEMPLATES.items():
        assert isinstance(templates, list), f"Hook type {hook_type} templates should be a list"
        assert len(templates) > 0, f"Hook type {hook_type} should have at least one template"
        for template in templates:
            assert isinstance(template, str), f"Each template should be a string in {hook_type}"
            assert len(template) > 0, f"Each template should not be empty in {hook_type}"


def test_get_hook_templates_mystery():
    """mystery タイプのフックテンプレート取得テスト"""
    templates = get_hook_templates("mystery")
    assert isinstance(templates, list)
    assert len(templates) == 5
    assert "なぜ、彼女は俺の名を知っていたのか──" in templates
    assert "この鍵は、何を開けるために存在するのか？" in templates


def test_get_hook_templates_threat():
    """threat タイプのフックテンプレート取得テスト"""
    templates = get_hook_templates("threat")
    assert isinstance(templates, list)
    assert len(templates) == 5
    assert "その時、空が裂けた。奴が来る" in templates
    assert "警告は無視された。代償は大きすぎた" in templates


def test_get_hook_templates_emotion():
    """emotion タイプのフックテンプレート取得テスト"""
    templates = get_hook_templates("emotion")
    assert isinstance(templates, list)
    assert len(templates) == 5
    assert "『……もう、離さない』彼女の手が、震えていた" in templates
    assert "この思いを、言葉にすることはできないだろうか" in templates


def test_get_hook_templates_invalid_type():
    """不正なフックタイプの場合のエラーテスト"""
    with pytest.raises(ValueError, match="Invalid hook type: invalid"):
        get_hook_templates("invalid")


def test_get_all_hook_types():
    """すべてのフックタイプ取得テスト"""
    types = get_all_hook_types()
    assert isinstance(types, list)
    assert set(types) == {"mystery", "threat", "emotion"}
    assert len(types) == 3