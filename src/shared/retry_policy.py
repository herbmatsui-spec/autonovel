from __future__ import annotations

from typing import List, Tuple

from pydantic import BaseModel, ConfigDict, Field


class RetryPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_backoff: bool = True
    jitter: bool = True
    retryable_status_codes: Tuple[int, ...] = Field(
        default_factory=lambda: (429, 500, 502, 503, 504)
    )

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculates the delay for the given attempt number (0-indexed).
        """
        import random

        delay = self.base_delay
        if self.exponential_backoff and attempt > 0:
            delay = self.base_delay * (2 ** attempt)

        delay = min(delay, self.max_delay)

        if self.jitter:
            delay = delay * (0.5 + random.random())

        return delay
