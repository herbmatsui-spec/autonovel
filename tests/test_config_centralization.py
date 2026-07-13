import pytest

from config.project_context import ProjectContext, get_config
from config.settings import ConfigManager
from config.validator import ConfigValidator
from schemas.config import GlobalConfigModel


def _reset_config_cache():
    """ConfigManager / project_context のメモリキャッシュをリセット"""
    ConfigManager._instance = None
    import config.project_context as pc
    pc._global_config = None


@pytest.fixture(autouse=True)
def reset_cache():
    _reset_config_cache()
    yield
    _reset_config_cache()


def test_settings_toml_is_ssot():
    """settings.toml がスカラー設定の単一真理源であることを確認"""
    configs = ConfigValidator.validate_all()
    cfg = configs["settings"]
    assert isinstance(cfg, GlobalConfigModel)

    # TOML に定義した値が反映されていること
    assert cfg.model_writing == "gemma-4-31b-it"
    assert cfg.auto_backup is True
    assert cfg.cooldown_max == 90.0
    assert cfg.stress_catharsis_threshold == 85
    assert cfg.safe_append_mode == "auto"
    assert cfg.draft_polish_enabled is True
    assert cfg.fail_fast_mode is False
    assert cfg.enable_nsfw is False


def test_env_override_explicit_merge(monkeypatch):
    """許可された環境変数のみが SSOT を上書きすることを確認"""
    monkeypatch.setenv("KAKU_FAIL_FAST_MODE", "true")
    monkeypatch.setenv("REDIS_URL", "redis://example:6379/1")
    # マッピング外の環境変数は無視されること
    monkeypatch.setenv("RANDOM_UNMAPPED_VAR", "should_be_ignored")

    _reset_config_cache()
    cfg = get_config()

    assert cfg.fail_fast_mode is True
    assert cfg.redis_url == "redis://example:6379/1"
    # 影響なし: デフォルト維持
    assert cfg.enable_nsfw is False


def test_env_override_type_coercion(monkeypatch):
    """環境変数の文字列がフィールド型に変換されることを確認"""
    monkeypatch.setenv("KAKU_MAX_CONCURRENCY", "4")
    monkeypatch.setenv("KAKU_CONTEXT_WINDOW_TARGET_RATIO", "0.5")

    _reset_config_cache()
    cfg = get_config()

    assert cfg.max_concurrency == 4
    assert isinstance(cfg.max_concurrency, int)
    assert cfg.context_window_target_ratio == 0.5
    assert isinstance(cfg.context_window_target_ratio, float)


def test_env_override_missing_is_ignored(monkeypatch):
    """マッピング外の環境変数は設定に影響しないことを確認"""
    monkeypatch.delenv("KAKU_FAIL_FAST_MODE", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    _reset_config_cache()
    cfg = get_config()
    assert cfg.fail_fast_mode is False  # TOML のデフォルト


def test_consistency_validation_detects_errors():
    """論理整合性検証が異常値を検出することを確認"""
    bad = GlobalConfigModel(cooldown_min=100.0, cooldown_max=10.0)
    errors = bad.validate_consistency()
    assert any("cooldown_min" in e for e in errors)

    good = GlobalConfigModel()
    assert good.validate_consistency() == []


def test_configmanager_is_canonical_accessor():
    """ConfigManager がキャッシュ付きで設定を返すことを確認"""
    _reset_config_cache()
    a = ConfigManager.get_config()
    b = ConfigManager.get_config()
    assert a is b  # 同一インスタンス (キャッシュ)
    assert a.model_writing == "gemma-4-31b-it"


def test_projectcontext_delegates_to_canonical(monkeypatch):
    """ProjectContext.get_setting が SSOT 経由の値を返すことを確認"""
    monkeypatch.setenv("KAKU_FAIL_FAST_MODE", "true")
    _reset_config_cache()
    assert ProjectContext.get_setting("fail_fast_mode") is True
