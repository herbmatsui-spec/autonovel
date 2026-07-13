from config.models import GlobalConfigModel
from config.project_context import get_config


def test_global_config_model_loading():
    """GlobalConfigModel が正しく読み込めることを確認"""
    config = GlobalConfigModel.default()
    assert config.model_writing is not None
    assert isinstance(config.model_writing, str)

def test_config_initialization():
    """get_config() で設定が初期化されることを確認"""
    config = get_config()
    assert config is not None
    assert hasattr(config, "model_writing")

if __name__ == "__main__":
    test_global_config_model_loading()
    test_config_initialization()
    print("Config tests passed!")
