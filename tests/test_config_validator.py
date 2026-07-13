#!/usr/bin/env python3
"""
config/validator.py の統合テスト

新しい機能:
  - strict=False モード（部分成功）
  - GlobalConfigModel.load() の委譲パターン
  - models.yaml → settings マージ
  - エラーメッセージ改善
"""
from contextlib import contextmanager
from pathlib import Path

import pytest

from config.project_context import get_config
from config.validator import ConfigValidator
from schemas.config import GlobalConfigModel


class TestValidateAllStrictFalse:
    """strict=False モードのテスト"""

    @pytest.fixture(autouse=True)
    def _backup_cleanup(self):
        """各テスト後に.bakファイルを残さない"""
        yield
        for p in Path("config").glob("*.bak"):
            p.unlink(missing_ok=True)

    @staticmethod
    @contextmanager
    def _backup_and_restore(path: str):
        """ファイルを.bakにバックアップし、コンテキストマネージャーを返す"""
        p = Path(path)
        bak = Path(f"{path}.bak")
        if p.exists():
            if bak.exists():
                bak.unlink()
            p.rename(bak)
        try:
            yield
        finally:
            if bak.exists():
                if p.exists():
                    p.unlink()
                bak.rename(p)

    def test_missing_file_returns_default(self):
        """ファイルが欠けている場合、strict=False ではデフォルト値で代替される"""
        with self._backup_and_restore("config/settings.toml"):
            configs = ConfigValidator.validate_all(strict=False)
            assert "settings" in configs
            assert isinstance(configs["settings"], GlobalConfigModel)
            # デフォルト値で代替されている
            assert configs["settings"].model_writing == "gemma-4-31b-it"

    def test_multiple_files_missing(self):
        """複数ファイルが欠けていても strict=False では続行できる"""
        targets = ["config/settings.toml", "config/models.yaml", "config/tropes.json"]
        backups = {}
        try:
            for target in targets:
                p = Path(target)
                if p.exists():
                    bak = Path(f"{target}.bak")
                    if bak.exists():
                        bak.unlink()
                    p.rename(bak)
                    backups[target] = bak

            configs = ConfigValidator.validate_all(strict=False)
            assert "settings" in configs
            assert "models" in configs
            assert "tropes" in configs
            # すべてデフォルト値で代替
            assert configs["models"].planning == "gemini-3.1-flash-lite"
        finally:
            for original_path, bak in list(backups.items()):
                if bak.exists():
                    p = Path(original_path)
                    if p.exists():
                        p.unlink()
                    bak.rename(p)


class TestGlobalConfigModelLoad:
    """GlobalConfigModel.load() 委譲パターンのテスト"""

    def test_load_returns_global_config(self):
        """load() が GlobalConfigModel を返すことを確認"""
        config = GlobalConfigModel.load()
        assert isinstance(config, GlobalConfigModel)
        assert config.model_writing == "gemma-4-31b-it"

    def test_load_includes_merged_models(self):
        """load() の戻り値に models.yaml の値がマージされていることを確認"""
        config = GlobalConfigModel.load()
        # models.yaml の値が settings にマージされている
        assert config.model_planning == "gemini-3.1-flash-lite"
        assert config.model_plot_expansion == "gemma-4-31b-it"
        assert config.model_writing == "gemma-4-31b-it"

    def test_load_includes_domain_profiles(self):
        """load() の戻り値に domain_profiles が含まれていることを確認"""
        config = GlobalConfigModel.load()
        assert hasattr(config, "domain_profiles")
        assert len(config.domain_profiles) >= 2


class TestGetConfig:
    """project_context.get_config() のテスト"""

    def test_get_config_returns_merged(self):
        """get_config() がマージ済み設定を返すことを確認"""
        config = get_config()
        assert isinstance(config, GlobalConfigModel)
        # models.yaml の値が反映されている
        assert config.model_planning == "gemini-3.1-flash-lite"
        # tropes がマージされている
        assert hasattr(config, "tropes")
        assert len(config.tropes["tropes"]) > 0
        # system_plugins がマージされている
        assert hasattr(config, "system_plugins")


class TestModelMerging:
    """models.yaml → settings マージロジックのテスト"""

    def test_model_key_map_applied(self):
        """model_key_map の全キーが正しくマッピングされることを確認"""
        configs = ConfigValidator.validate_all()
        settings = configs["settings"]
        models = configs["models"]

        model_key_map = {
            "planning": "model_planning",
            "plot_expansion": "model_plot_expansion",
            "writing": "model_writing",
            "climax": "model_climax",
            "fallback": "model_stable_fallback",
            "ultra_stable": "model_ultra_stable",
        }

        for yaml_key, model_key in model_key_map.items():
            yaml_val = getattr(models, yaml_key, None)
            settings_val = getattr(settings, model_key, None)
            if yaml_val:
                assert settings_val == yaml_val, (
                    f"{model_key} に {yaml_key} の値 {yaml_val} が反映されていません"
                )


class TestErrorMessages:
    """エラーメッセージ改善のテスト"""

    def test_missing_file_error_includes_filename(self):
        """ファイル名を含むエラーメッセージが出力されることを確認"""
        with pytest.raises((FileNotFoundError, SystemExit)) as excinfo:
            ConfigValidator.load_settings_toml(path="config/nonexistent_file.toml")
        error_msg = str(excinfo.value)
        assert "nonexistent_file.toml" in error_msg or "見つかりません" in error_msg

    def test_validate_all_strict_error_message(self):
        """strict=True 時のエラーメッセージにファイル名が含まれることを確認"""
        with pytest.raises(FileNotFoundError) as excinfo:
            ConfigValidator.load_settings_toml(path="config/__missing_test_file__.toml")
        # ファイル名がエラーメッセージに含まれているか
        err = str(excinfo.value)
        assert "__missing_test_file__" in err or "見つかりません" in err


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
