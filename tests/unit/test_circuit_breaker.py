import time

from src.shared.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)


def test_circuit_breaker_initial_state():
    """初期状態が CLOSED でありリクエストを許可することを確認。"""
    cb = CircuitBreaker("test_service", CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0))
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True


def test_circuit_breaker_transition_to_open():
    """連続失敗により OPEN に遷移しリクエストが拒否されることを確認。"""
    cb = CircuitBreaker("test_service", CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1.0))

    # 1回目の失敗
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    assert cb.allow_request() is True

    # 2回目の失敗（閾値到達）
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False


def test_circuit_breaker_recovery_to_half_open_and_closed():
    """タイムアウト後に HALF_OPEN へ移行し、成功で CLOSED に復帰することを確認。"""
    cb = CircuitBreaker(
        "test_service",
        CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.05, half_open_max_success=1),
    )

    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False

    # タイムアウト待機
    time.sleep(0.06)

    # HALF_OPEN への遷移
    assert cb.allow_request() is True
    assert cb.state == CircuitState.HALF_OPEN

    # 成功を記録して CLOSED へ復帰
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_half_open_failure_reopens():
    """HALF_OPEN 状態で失敗した場合に即座に OPEN へ戻ることを確認。"""
    cb = CircuitBreaker(
        "test_service",
        CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.05),
    )

    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    time.sleep(0.06)
    assert cb.allow_request() is True
    assert cb.state == CircuitState.HALF_OPEN

    # HALF_OPEN での失敗
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.allow_request() is False
