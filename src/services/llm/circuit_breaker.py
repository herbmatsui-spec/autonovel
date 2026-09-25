"""LLMプロバイダー向けサーキットブレーカー (src.llm.circuit_breaker 統合版)。"""
from __future__ import annotations

from typing import Any
from src.llm.circuit_breaker import (
    CircuitState,
    LLMCircuitBreaker,
    ProviderHealthState,
)


class CircuitBreakerOpenException(Exception):
    """回路遮断中にリクエストが試行された場合の例外。"""
    pass


class CircuitBreaker:
    """単一プロバイダまたは共有インスタンスに対するアダプタクラス。
    内部でスレッドセーフな LLMCircuitBreaker を使用して状態管理を行う。
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        provider_name: str = "default",
        underlying: LLMCircuitBreaker | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._underlying = underlying or LLMCircuitBreaker(
            failure_threshold=failure_threshold,
            timeout_seconds=recovery_timeout,
            cooldown_seconds=recovery_timeout,
        )

    @property
    def state(self) -> CircuitState:
        return self._underlying.get_state(self.provider_name).state

    @property
    def failure_count(self) -> int:
        return self._underlying.get_state(self.provider_name).failure_count

    def record_success(self, provider_name: str | None = None) -> None:
        self._underlying.record_success(provider_name or self.provider_name)

    def record_failure(self, provider_name: str | None = None, error: Any = None) -> None:
        self._underlying.record_failure(provider_name or self.provider_name, error)

    def can_execute(self, provider_name: str | None = None) -> bool:
        return self._underlying.can_execute(provider_name or self.provider_name)


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpenException",
    "CircuitState",
    "LLMCircuitBreaker",
    "ProviderHealthState",
]
