import pytest
from pathlib import Path
from config.validator import ConfigValidator
from config.erotic_pacing import EroticCurve, HAS_EROTIC_PARAMETERS


def test_config_validator_path_resolution():
    """ConfigValidator が相対パスを柔軟に解決できることを検証"""
    resolved = ConfigValidator._resolve_config_path("config/settings.toml")
    assert isinstance(resolved, Path)
    assert resolved.exists()
    assert resolved.name == "settings.toml"


def test_config_validator_load_settings_toml():
    """settings.toml が正常に GlobalConfigModel としてロードされることを検証"""
    config = ConfigValidator.load_settings_toml("config/settings.toml")
    assert config is not None
    assert hasattr(config, "model_writing")


def test_erotic_pacing_type_safe_fallback():
    """erotic_pacing が型への不正代入なしに安全にデフォルト曲線を生成できることを検証"""
    curve = EroticCurve.create_default(intensity=2)
    assert curve is not None
    assert len(curve.beats) > 0
    assert curve.target_intensity == 2

    # create_from_parameters のフォールバック動作検証
    class MockParams:
        base_intensity = 3

    fallback_curve = EroticCurve.create_from_parameters(MockParams())
    assert fallback_curve is not None
