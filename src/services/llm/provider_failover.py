"""プロバイダーフェイルオーバーマネージャー。"""
from __future__ import annotations
from typing import Any, Callable, Coroutine
from src.services.llm.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException


class ProviderFailoverManager:
    def __init__(self):
        self.breakers: dict[str, CircuitBreaker] = {
            "gemini": CircuitBreaker(failure_threshold=3, recovery_timeout=30.0),
            "openai": CircuitBreaker(failure_threshold=3, recovery_timeout=30.0),
            "claude": CircuitBreaker(failure_threshold=3, recovery_timeout=30.0),
        }

    async def execute_with_fallback(
        self,
        primary_provider: str,
        fallback_provider: str,
        primary_fn: Callable[[], Coroutine[Any, Any, Any]],
        fallback_fn: Callable[[], Coroutine[Any, Any, Any]],
    ) -> tuple[Any, str]:
        """Primaryで試行し、遮断または失敗時にFallbackを実行する。"""
        p_breaker = self.breakers.get(primary_provider, self.breakers["gemini"])
        f_breaker = self.breakers.get(fallback_provider, self.breakers["openai"])

        if p_breaker.can_execute():
            try:
                res = await primary_fn()
                p_breaker.record_success()
                return res, primary_provider
            except Exception:
                p_breaker.record_failure()

        # Fallback 実行
        if not f_breaker.can_execute():
            raise CircuitBreakerOpenException("すべての利用可能なプロバイダーが遮断されています")
        
        try:
            res = await fallback_fn()
            f_breaker.record_success()
            return res, fallback_provider
        except Exception as e:
            f_breaker.record_failure()
            raise e