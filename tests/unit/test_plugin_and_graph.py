import pytest
from src.core.plugin_loader import PluginLoader
from src.core.plugin_schema import ArchetypePreset


@pytest.mark.skip(reason="PluginLoader.get_plugin() は未実装。plugins/ ディレクトリが空のためスキップ")
def test_archetype_visual_metadata_loading():
    """
    Phase 9: 統合テスト
    アーキタイプのビジュアルメタデータ（visual_icon, summary, trend_tag）が
    正しくロードされ、スキーマに従っているかを確認する。
    """
    loader = PluginLoader.get_instance()
    # standard_archetypes プラグインを明示的にロード/取得
    plugin = loader.get_plugin("standard_archetypes")

    assert plugin is not None, "standard_archetypes plugin should be loaded"
    assert plugin.archetypes is not None, "Plugin should have archetypes defined"

    # 代表的なアーキタイプでメタデータを検証
    target_key = "王道ざまぁ（爽快感最大）"
    assert target_key in plugin.archetypes, f"{target_key} should be in archetypes"

    preset = plugin.archetypes[target_key]
    assert isinstance(preset, ArchetypePreset)

    # 追加したビジュアルフィールドの存在確認
    assert preset.visual_icon is not None, "visual_icon should be defined"
    assert preset.summary is not None, "summary should be defined"
    assert preset.trend_tag is not None, "trend_tag should be defined"

    # 具体的な値の検証（yamlの定義と一致しているか）
    assert preset.visual_icon == "sword"
    assert "追放された主人公" in preset.summary
    assert preset.trend_tag == "Web小説の王道"


@pytest.mark.skip(reason="PluginLoader.get_plugin() は未実装。plugins/ ディレクトリが空のためスキップ")
def test_custom_archetype_defaults():
    """
    カスタムアーキタイプなど、メタデータが空の場合にNoneまたはデフォルト値になるか確認
    """
    loader = PluginLoader.get_instance()
    plugin = loader.get_plugin("standard_archetypes")

    preset = plugin.archetypes.get("カスタム")
    assert preset is not None
    # カスタムアーキタイプのデフォルト値を確認
    assert preset.visual_icon == "settings"
    assert "オリジナルの物語" in preset.summary
    assert preset.trend_tag == "自由設計"
