import time
from src.services.llm.circuit_breaker import CircuitBreaker, CircuitState

def test_circuit_breaker_transitions_to_open():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.1)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # 3回連続失敗
    cb.record_failure()
    cb.record_failure()
    cb.record_failure()

    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # タイムアウト経過後は HALF_OPEN に遷移
    time.sleep(0.15)
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # 成功を記録して CLOSED に復旧
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
