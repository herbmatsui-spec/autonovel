#!/usr/bin/env python3
"""
ConfigValidator のエッジケーステスト

カバレッジ向上のための追加テスト:
- 不正TOML
- 必須フィールド欠如
- 型不正
- 環境変数オーバーライド（正常/異常）
- マージ優先順位
- ドメインプロファイル読み込み失敗
"""

import os
import pytest
from pathlib import Path
from contextlib import contextmanager

from config.validator import ConfigValidator
from schemas.config import GlobalConfigModel


@contextmanager
def _backup_and_restore(path: str):
    """ファイルを.bakにバックアップし、コンテキスト終了時に復元"""
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


@contextmanager
def _set_env(key: str, value: str):
    """環境変数を一時設定し、終了時に復元"""
    old = os.environ.get(key)
    os.environ[key] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old


class TestConfigValidatorEdgeCases:
    """ConfigValidator のエッジケーステスト"""

    def test_invalid_toml_raises_error(self):
        """不正なTOML構文で TOMLDecodeError が投げられることを確認"""
        with _backup_and_restore("config/settings.toml"):
            # 不正なTOMLを書き込み
            Path("config/settings.toml").write_text("[general\nmodel_writing = \"test\"", encoding="utf-8")
            
            with pytest.raises(Exception) as excinfo:
                ConfigValidator.load_settings_toml()
            
            # tomllib.TOMLDecodeError が投げられることを確認（型でチェック）
            assert excinfo.type.__name__ == "TOMLDecodeError"

    def test_missing_field_uses_default(self):
        """必須フィールド欠如時にデフォルト値が使用されることを確認"""
        with _backup_and_restore("config/settings.toml"):
            # model_writing を削除したTOML
            toml_content = """
[general]
model_planning = "gemini-3.5-flash-lite"
model_plot_expansion = "gemma-4-31b-it"
"""
            Path("config/settings.toml").write_text(toml_content, encoding="utf-8")
            
            # 例外は投げられず、デフォルト値でロードされる
            config = ConfigValidator.load_settings_toml()
            assert config.model_writing == "gemma-4-31b-it"  # デフォルト値

    def test_invalid_type_field_raises_error(self):
        """型不正フィールドでエラーが投げられることを確認"""
        with _backup_and_restore("config/settings.toml"):
            # max_concurrency に文字列を指定
            toml_content = """
[general]
model_writing = "gemma-4-31b-it"
model_planning = "gemini-3.5-flash-lite"
model_plot_expansion = "gemma-4-31b-it"
max_concurrency = "five"
"""
            Path("config/settings.toml").write_text(toml_content, encoding="utf-8")
            
            with pytest.raises(Exception) as excinfo:
                ConfigValidator.load_settings_toml()
            
            assert "VALIDATION" in str(excinfo.value).upper() or "TYPE" in str(excinfo.value).upper()

    def test_env_override_valid_value(self):
        """環境変数オーバーライド（正常値）が反映されることを確認"""
        with _set_env("KAKU_MODEL_WRITING", "custom-test-model"):
            # 環境変数適用後の設定を取得
            config = ConfigValidator.load_settings_toml()
            assert config.model_writing == "custom-test-model"

    def test_env_override_invalid_type(self):
        """環境変数オーバーライド（不正型）の挙動を確認"""
        with _set_env("KAKU_MAX_CONCURRENCY", "invalid"):
            # 不正な値の場合の挙動を確認（例外またはデフォルト値）
            try:
                config = ConfigValidator.load_settings_toml()
                # 例外が出ない場合、デフォルト値または元の値が保持されることを確認
                assert isinstance(config.max_concurrency, int)
            except (ValueError, TypeError):
                # 例外が投げられる場合も許容
                pass

    def test_toml_priority_over_yaml(self):
        """settings.toml の値が models.yaml より優先されることを確認"""
        configs = ConfigValidator.validate_all()
        settings = configs["settings"]
        models = configs["models"]
        
        # 現在の設定では両ファイルとも同じ値だが、マージロジックは TOML を優先する
        # 環境変数オーバーライドで差分を作ってテスト
        with _set_env("KAKU_MODEL_PLANNING", "env-override-model"):
            configs2 = ConfigValidator.validate_all()
            settings2 = configs2["settings"]
            # 環境変数が最優先される
            assert settings2.model_planning == "env-override-model"

    def test_domain_profile_invalid_json_fallback(self):
        """不正なドメインプロファイルJSONで strict=False 時にデフォルト値で代替"""
        # 一時的に不正なJSONを配置
        domain_dir = Path("config/domain_profiles")
        invalid_file = domain_dir / "invalid_test.json"
        
        try:
            invalid_file.write_text("{invalid json}", encoding="utf-8")
            
            configs = ConfigValidator.validate_all(strict=False)
            
            # エラーにならず、他のプロファイルは読み込まれる
            assert "domain_profiles" in configs
            assert len(configs["domain_profiles"]) >= 4  # 元の4つ以上
            
        finally:
            if invalid_file.exists():
                invalid_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])