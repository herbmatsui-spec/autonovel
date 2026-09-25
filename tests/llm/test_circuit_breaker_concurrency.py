"""
tests/llm/test_circuit_breaker_concurrency.py
Part 4 (Step 13-15) リグレッション防止テスト:
統合された LLMCircuitBreaker および CircuitBreaker のマルチスレッド安全性、
プロバイダ別障害分離、および状態遷移（CLOSED -> OPEN -> HALF_OPEN -> CLOSED）を検証。
"""

import threading
import time
import pytest
from src.llm.circuit_breaker import LLMCircuitBreaker, CircuitState
from src.services.llm.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from src.services.llm.provider_failover import ProviderFailoverManager


def test_circuit_breaker_state_transitions():
    """3回失敗で OPEN、成功で CLOSED に戻る状態遷移の検証"""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.2)
    assert cb.can_execute() is True
    assert cb.state == CircuitState.CLOSED

    # 1回目、2回目失敗
    cb.record_failure()
    assert cb.can_execute() is True
    cb.record_failure()
    assert cb.can_execute() is True

    # 3回目失敗 -> OPEN へ遷移
    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # リカバリータイムアウト待機 (0.2秒以上)
    time.sleep(0.25)
    assert cb.can_execute() is True  # HALF_OPEN へ試験復旧

    # 成功を記録 -> CLOSED へ復帰
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True


def test_circuit_breaker_provider_isolation():
    """プロバイダ間でサーキット状態が完全に独立していることを検証"""
    shared_engine = LLMCircuitBreaker(failure_threshold=2, timeout_seconds=10)

    cb_gemini = CircuitBreaker(provider_name="gemini", underlying=shared_engine)
    cb_openai = CircuitBreaker(provider_name="openai", underlying=shared_engine)

    # Gemini を2回連続失敗させて OPEN にする
    cb_gemini.record_failure()
    cb_gemini.record_failure()
    assert cb_gemini.can_execute() is False
    assert cb_gemini.state == CircuitState.OPEN

    # OpenAI は影響を受けず CLOSED のままであること
    assert cb_openai.can_execute() is True
    assert cb_openai.state == CircuitState.CLOSED


def test_circuit_breaker_thread_safety():
    """マルチスレッドからの並行アクセスで競合や不整合が発生しないことを検証"""
    cb = CircuitBreaker(failure_threshold=100, recovery_timeout=1.0)

    def worker_failures():
        for _ in range(50):
            cb.record_failure()

    def worker_successes():
        for _ in range(50):
            cb.record_success()

    threads = []
    for _ in range(5):
        t1 = threading.Thread(target=worker_failures)
        t2 = threading.Thread(target=worker_successes)
        threads.extend([t1, t2])

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # スレッドセーフに実行され、例外等でクラッシュしないこと
    assert isinstance(cb.state, CircuitState)


def test_provider_failover_integration():
    """ProviderFailoverManager が統合サーキットブレーカーと協調して動作することを検証"""
    mgr = ProviderFailoverManager()
    assert mgr.breakers["gemini"].can_execute() is True

    # gemini を3回失敗させて遮断
    for _ in range(3):
        mgr.breakers["gemini"].record_failure()

    assert mgr.breakers["gemini"].can_execute() is False
    # openai は利用可能であること
    assert mgr.breakers["openai"].can_execute() is True
