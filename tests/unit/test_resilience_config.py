from src.shared.resilience_config import ResilienceConfigLoader, resilience_config


def test_resilience_config_singleton():
    """シングルトンインスタンスの検証。"""
    loader1 = ResilienceConfigLoader()
    loader2 = ResilienceConfigLoader()
    assert loader1 is loader2
    assert resilience_config is loader1


def test_resilience_config_get_policy_for_service():
    """デフォルトおよびサービス別設定取得の検証。"""
    policy, cb_config = resilience_config.get_policy_for_service("llm_service")

    assert policy.max_attempts >= 1
    assert cb_config.failure_threshold >= 1
    assert cb_config.recovery_timeout > 0


def test_resilience_config_unknown_service_fallback():
    """未知のサービス名の場合にデフォルト設定へフォールバックすることの検証。"""
    policy, cb_config = resilience_config.get_policy_for_service("non_existent_service")

    assert policy is not None
    assert cb_config is not None
    assert policy.max_attempts == 3
