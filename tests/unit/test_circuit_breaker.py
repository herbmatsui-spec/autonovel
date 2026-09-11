import asyncio
import pytest

from src.llm.circuit_breaker import LLMCircuitBreaker, CircuitState


def test_circuit_breaker_basic():
    """サーキットブレーカーの基本動作をテスト"""
    breaker = LLMCircuitBreaker(failure_threshold=3, timeout_seconds=5)

    # プロバイダの状態を取得
    state = breaker.get_state("test_provider")
    assert state.state == CircuitState.CLOSED

    # 初期状態では実行可能
    assert breaker.can_execute("test_provider") == True

    # 連続失敗 -> Open状態に移行
    breaker.record_failure("test_provider")
    breaker.record_failure("test_provider")
    breaker.record_failure("test_provider")  # 3 failures -> OPEN
    assert breaker.can_execute("test_provider") == False

    # 復旧後も実行不可
    breaker.record_failure("test_provider")
    assert breaker.can_execute("test_provider") == False

    # 成功を記録すると復旧しない (OPEN -> still OPEN, success doesn't help)
    breaker.record_success("test_provider")
    assert breaker.can_execute("test_provider") == False


async def test_circuit_breaker_half_open():
    """サーキットブレーカーのHALF_OPEN状態をテスト"""
    breaker = LLMCircuitBreaker(failure_threshold=1, timeout_seconds=0.1)

    # 失敗でOpen状態に
    breaker.record_failure("test_provider")
    assert breaker.can_execute("test_provider") == False

    # タイムアウト後、HALF_OPEN状態になる
    await asyncio.sleep(0.15)

    # HALF_OPEN状態は1回の呼び出しまで可能
    assert breaker.can_execute("test_provider") == True

    # HALF_OPEN の probe に成功すると CLOSED に復帰
    breaker.record_success("test_provider")
    assert breaker.get_state("test_provider").state == CircuitState.CLOSED
    assert breaker.can_execute("test_provider") == True


def test_circuit_breaker_closed_success_count():
    """サーキットブレーカーの成功カウントをテスト"""
    breaker = LLMCircuitBreaker(failure_threshold=3)

    # 最初は成功カウントが0
    state = breaker.get_state("test_provider")
    assert state.success_count == 0

    # 成功を記録
    breaker.record_success("test_provider")
    state = breaker.get_state("test_provider")
    assert state.success_count == 1

    # 複数回の成功
    breaker.record_success("test_provider")
    breaker.record_success("test_provider")
    state = breaker.get_state("test_provider")
    assert state.success_count == 3


async def test_circuit_breaker_reset():
    """サーキットブレーカーのリセット機能"""
    breaker = LLMCircuitBreaker(failure_threshold=1, timeout_seconds=5)
    breaker.record_failure("test_provider")
    assert breaker.can_execute("test_provider") == False

    breaker.reset("test_provider")
    assert breaker.can_execute("test_provider") == True


async def test_circuit_breaker_snapshot():
    """サーキットブレーカーのスナップショット取得"""
    breaker = LLMCircuitBreaker(failure_threshold=1, timeout_seconds=5)
    breaker.record_failure("test_provider")
    state = breaker.snapshot()["test_provider"]
    assert state["state"] == "open"
    assert state["failure_count"] == 1


if __name__ == "__main__":
    test_circuit_breaker_basic()
    asyncio.run(test_circuit_breaker_half_open())
    test_circuit_breaker_closed_success_count()
    asyncio.run(test_circuit_breaker_reset())
    asyncio.run(test_circuit_breaker_snapshot())
    print("All tests passed!")
