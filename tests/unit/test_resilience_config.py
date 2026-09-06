import tempfile
import os
from unittest.mock import patch, mock_open

import pytest

from src.shared.resilience_config import ResilienceConfigLoader
from src.shared.circuit_breaker import CircuitBreakerConfig
from src.shared.retry_policy import RetryPolicy


class TestResilienceConfigLoader:
    def test_singleton_instance(self):
        """シングルトンインスタンスの検証。"""
        loader1 = ResilienceConfigLoader()
        loader2 = ResilienceConfigLoader()
        assert loader1 is loader2

    def test_load_config_file_not_found_uses_defaults(self):
        """設定ファイルが存在しない場合にデフォルト設定を使用する。"""
        # 存在しないパスを指定
        with patch.object(ResilienceConfigLoader, "_config_path", "/nonexistent/path.yaml"):
            # シングルトンをリセット
            ResilienceConfigLoader._instance = None
            loader = ResilienceConfigLoader()
            assert loader._config_data == {}

    def test_load_config_yaml_parse_error_uses_defaults(self):
        """YAMLパースエラー時にデフォルト設定を使用する。"""
        invalid_yaml = "invalid: yaml: content: ["
        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with patch("os.path.exists", return_value=True):
                ResilienceConfigLoader._instance = None
                loader = ResilienceConfigLoader()
                assert loader._config_data == {}

    def test_load_config_valid_yaml(self):
        """有効なYAMLが正しく読み込まれる。"""
        valid_yaml = """
default:
  retry_policy:
    max_attempts: 5
  circuit_breaker:
    failure_threshold: 10
services:
  llm_service:
    retry_policy:
      base_delay: 2.0
"""
        with patch("builtins.open", mock_open(read_data=valid_yaml)):
            with patch("os.path.exists", return_value=True):
                ResilienceConfigLoader._instance = None
                loader = ResilienceConfigLoader()
                assert loader._config_data["default"]["retry_policy"]["max_attempts"] == 5
                assert loader._config_data["services"]["llm_service"]["retry_policy"]["base_delay"] == 2.0

    def test_get_policy_for_service_with_service_specific_config(self):
        """サービス固有設定が正しくマージされる。"""
        valid_yaml = """
default:
  retry_policy:
    max_attempts: 3
    base_delay: 1.0
  circuit_breaker:
    failure_threshold: 5
services:
  custom_service:
    retry_policy:
      max_attempts: 10
      base_delay: 0.5
"""
        with patch("builtins.open", mock_open(read_data=valid_yaml)):
            with patch("os.path.exists", return_value=True):
                ResilienceConfigLoader._instance = None
                loader = ResilienceConfigLoader()
                policy, cb_config = loader.get_policy_for_service("custom_service")

                # サービス固有設定が優先
                assert policy.max_attempts == 10
                assert policy.base_delay == 0.5
                # デフォルトから継承
                assert cb_config.failure_threshold == 5

    def test_get_policy_for_service_unknown_uses_default(self):
        """未知のサービスはデフォルト設定を使用する。"""
        valid_yaml = """
default:
  retry_policy:
    max_attempts: 7
  circuit_breaker:
    failure_threshold: 3
"""
        with patch("builtins.open", mock_open(read_data=valid_yaml)):
            with patch("os.path.exists", return_value=True):
                ResilienceConfigLoader._instance = None
                loader = ResilienceConfigLoader()
                policy, cb_config = loader.get_policy_for_service("unknown_service")

                assert policy.max_attempts == 7
                assert cb_config.failure_threshold == 3

    def test_get_policy_for_service_empty_config_uses_dataclass_defaults(self):
        """空の設定ではデータクラスのデフォルト値が使用される。"""
        with patch("os.path.exists", return_value=False):
            ResilienceConfigLoader._instance = None
            loader = ResilienceConfigLoader()
            policy, cb_config = loader.get_policy_for_service("any_service")

            assert policy.max_attempts == 3  # RetryPolicy default
            assert policy.base_delay == 1.0
            assert cb_config.failure_threshold == 5  # CircuitBreakerConfig default
            assert cb_config.recovery_timeout == 30.0

    def test_get_policy_for_service_partial_override(self):
        """一部の設定のみオーバーライドされる。"""
        valid_yaml = """
default:
  retry_policy:
    max_attempts: 3
    base_delay: 1.0
    exponential_backoff: true
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 30.0
services:
  partial_service:
    retry_policy:
      max_attempts: 8  # のみオーバーライド
"""
        with patch("builtins.open", mock_open(read_data=valid_yaml)):
            with patch("os.path.exists", return_value=True):
                ResilienceConfigLoader._instance = None
                loader = ResilienceConfigLoader()
                policy, cb_config = loader.get_policy_for_service("partial_service")

                assert policy.max_attempts == 8  # オーバーライド済み
                assert policy.base_delay == 1.0  # デフォルト継承
                assert policy.exponential_backoff is True  # デフォルト継承
                assert cb_config.failure_threshold == 5  # デフォルト継承

    def test_global_resilience_config_instance(self):
        """グローバルインスタンスが正しく初期化される。"""
        from src.shared.resilience_config import resilience_config
        assert isinstance(resilience_config, ResilienceConfigLoader)

    def test_config_data_isolation_between_instances(self):
        """シングルトンなのでインスタンス間で設定が共有される。"""
        loader1 = ResilienceConfigLoader()
        loader2 = ResilienceConfigLoader()
        assert loader1._config_data is loader2._config_data