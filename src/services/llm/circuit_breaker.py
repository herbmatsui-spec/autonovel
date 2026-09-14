"""LLMプロバイダー向けサーキットブレーカー。"""
from __future__ import annotations
import time
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"      # 正常稼働
    OPEN = "open"          # 遮断中 (通信スキップ)
    HALF_OPEN = "half_open"  # 試験復旧中


class CircuitBreakerOpenException(Exception):
    """回路遮断中にリクエストが試行された場合の例外。"""
    pass


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0

    def record_success(self) -> None:
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def can_execute(self) -> bool:
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True