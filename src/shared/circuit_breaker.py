import threading
import time
from enum import Enum

from pydantic import BaseModel


class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerConfig(BaseModel):
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_success: int = 2


class CircuitBreaker:
    def __init__(self, name: str, config: CircuitBreakerConfig = CircuitBreakerConfig()):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float = 0.0
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time >= self.config.recovery_timeout:
                    print(f"[CircuitBreaker:{self.name}] Transitioning from OPEN to HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                    return True
                return False
            if self.state == CircuitState.HALF_OPEN:
                return True
            return False

    def record_success(self):
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.half_open_max_success:
                    print(f"[CircuitBreaker:{self.name}] Transitioning from HALF_OPEN to CLOSED")
                    self._reset()
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def record_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    print(f"[CircuitBreaker:{self.name}] Transitioning from CLOSED to OPEN (failures: {self.failure_count})")
                    self.state = CircuitState.OPEN
            elif self.state == CircuitState.HALF_OPEN:
                print(f"[CircuitBreaker:{self.name}] Transitioning from HALF_OPEN to OPEN (probe failed)")
                self.state = CircuitState.OPEN
                self.success_count = 0

    def _reset(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
