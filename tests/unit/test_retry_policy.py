from src.shared.retry_policy import RetryPolicy


def test_retry_policy_defaults():
    """デフォルト設定値の検証。"""
    policy = RetryPolicy()
    assert policy.max_attempts == 3
    assert policy.base_delay == 1.0
    assert policy.max_delay == 30.0
    assert policy.exponential_backoff is True
    assert policy.jitter is True
    assert 500 in policy.retryable_status_codes
    assert 429 in policy.retryable_status_codes


def test_retry_policy_calculate_delay_exponential_no_jitter():
    """ジッター無効時の指数バックオフ遅延計算の検証。"""
    policy = RetryPolicy(base_delay=2.0, exponential_backoff=True, jitter=False, max_delay=60.0)

    assert policy.calculate_delay(0) == 2.0
    assert policy.calculate_delay(1) == 4.0
    assert policy.calculate_delay(2) == 8.0
    assert policy.calculate_delay(3) == 16.0


def test_retry_policy_calculate_delay_max_cap():
    """最大遅延上限 (max_delay) でキャップされることの検証。"""
    policy = RetryPolicy(base_delay=10.0, exponential_backoff=True, jitter=False, max_delay=15.0)

    assert policy.calculate_delay(0) == 10.0
    assert policy.calculate_delay(1) == 15.0  # 20.0 -> 15.0
    assert policy.calculate_delay(2) == 15.0  # 40.0 -> 15.0


def test_retry_policy_calculate_delay_with_jitter():
    """ジッター有効時に遅延が [0.5 * delay, 1.5 * delay] の範囲に収まることの検証。"""
    policy = RetryPolicy(base_delay=4.0, exponential_backoff=False, jitter=True, max_delay=30.0)

    for _ in range(20):
        delay = policy.calculate_delay(0)
        assert 2.0 <= delay <= 6.0
