from unittest.mock import MagicMock

from src.services.prompt_registry import PromptRegistry


def test_prompt_registry_render_and_metrics():
    """PromptRegistry でのテンプレートレンダリングとメトリクス追跡の検証。"""
    mock_pm = MagicMock()
    mock_template = MagicMock()
    mock_template.render.return_value = "Hello World: Taro"
    mock_pm.get_template.return_value = mock_template

    registry = PromptRegistry(mock_pm)

    # 取得実行
    rendered = registry.get("greeting_template", name="Taro")
    assert rendered == "Hello World: Taro"
    mock_template.render.assert_called_once_with(name="Taro")

    # メトリクス確認
    all_metrics = registry.get_metrics()
    assert "greeting_template" in all_metrics
    assert all_metrics["greeting_template"]["hits"] == 1
    assert all_metrics["greeting_template"]["total_time_ms"] >= 0


def test_prompt_registry_reset_metrics():
    """メトリクスのリセット機能の検証。"""
    mock_pm = MagicMock()
    mock_pm.get_template.return_value.render.return_value = "output"

    registry = PromptRegistry(mock_pm)
    registry.get("temp1")
    assert registry.get_metrics()["temp1"]["hits"] == 1

    registry.reset_metrics("temp1")
    assert "temp1" not in registry.get_metrics()
