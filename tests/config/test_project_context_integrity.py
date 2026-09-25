"""
config/project_context.py の整合性とリグレッション防止テスト
"""

import pytest
from config.project_context import ProjectContext, get_config, set_config
from config.models import GlobalConfigModel


def test_project_context_imports_and_get_config():
    """設定シングルトンが正常に取得でき、GlobalConfigModelのインスタンスであること"""
    cfg = get_config()
    assert isinstance(cfg, GlobalConfigModel)


def test_project_context_get_and_set_setting():
    """ProjectContext経由での設定値取得・上書き・デフォルト値動作の検証"""
    # 存在しないキーに対してデフォルト値を返すこと
    non_existent = ProjectContext.get_setting("non_existent_key_12345", default="fallback")
    assert non_existent == "fallback"

    # 既存設定の取得
    model = ProjectContext.get_setting("model_writing")
    assert model is not None

    # 設定値の一時的上書き
    original_value = model
    try:
        ProjectContext.set_setting("model_writing", "custom-test-model")
        assert ProjectContext.get_setting("model_writing") == "custom-test-model"
    finally:
        ProjectContext.set_setting("model_writing", original_value)
        assert ProjectContext.get_setting("model_writing") == original_value


def test_project_context_reset_overrides():
    """reset_overridesでデフォルト状態に戻ること"""
    ProjectContext.reset_overrides()
    cfg = get_config()
    assert isinstance(cfg, GlobalConfigModel)
