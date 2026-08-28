"""Async execution core with unified retry, circuit breaker, timeout, and backpressure."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import (
    Any,
    AsyncGenerator,
    AsyncIterator,
    Callable,
    Coroutine,
    Generic,
    Optional,
    TypeVar,
    Union,
)

# Import local modules
from ..shared.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenException,
)
from ..shared.retry_policy import RetryPolicy

logger = logging.getLogger(__name__)

T = TypeVar("T")
U = TypeVar("U")


@dataclass
class AsyncExecutorConfig:
    """Configuration for AsyncExecutor."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    jitter: bool = True
    exponential_backoff: bool = True
    timeout_seconds: Optional[float] = None
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    retryable_status_codes: tuple[int, ...] = (429, 500, 502, 503, 504)
    max_concurrency: int = 1  # Semaphore limit

    def get_retry_policy(self) -> RetryPolicy:
        """Create a RetryPolicy based on config."""
        return RetryPolicy(
            max_attempts=self.max_retries,
            base_delay=self.base_delay,
            max_delay=self.max_delay,
            exponential_backoff=self.exponential_backoff,
            jitter=self.jitter,
            retryable_status_codes=self.retryable_status_codes,
        )


class AsyncExecutionError(Exception):
    """Unified exception for async execution failures."""

    original_exception: Optional[Exception]

    def __init__(self, message: str, original_exception: Optional[Exception] = None):
        super().__init__(message)
        self.original_exception = original_exception


class AsyncExecutor(Generic[T]):
    """Core async execution engine with unified resilience patterns."""

    def __init__(self, config: AsyncExecutorConfig, name: str = "AsyncExecutor"):
        self.config = config
        self.name = name
        self.semaphore = asyncio.Semaphore(config.max_concurrency)
        self.circuit_breaker = CircuitBreaker(
            name, config.circuit_breaker_config or CircuitBreakerConfig()
        )
        self.retry_policy = config.get_retry_policy()
        self.active_tasks: set[asyncio.Task] = set()
        self.original_result: Optional[T] = None
        self.errors: list[Exception] = []

    async def __aenter__(self) -> AsyncExecutor[T]:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        for task in list(self.active_tasks):
            task.cancel()
        if self.active_tasks:
            await asyncio.gather(*self.active_tasks, return_exceptions=True)
        self.active_tasks.clear()

    def _cleanup(self) -> None:
        """Clean up resources after execution."""
        for task in list(self.active_tasks):
            task.cancel()
        self.active_tasks.clear()

    def _is_retryable(self, exc: Exception) -> bool:
        """Determine if an exception is retryable."""
        if isinstance(exc, CircuitBreakerOpenException):
            return False

        # Always retryable
        if isinstance(exc, asyncio.TimeoutError):
            return True

        # Retryable HTTP errors
        if (
            hasattr(exc, "status_code")
            and exc.status_code in self.retry_policy.retryable_status_codes
        ):
            return True

        # Recursively check wrapped exceptions
        if isinstance(exc, AsyncExecutionError):
            if "timed out" in str(exc).lower():
                return True
            if exc.original_exception:
                return self._is_retryable(exc.original_exception)

        return False

    async def _execute_with_timeout(self, coro: Coroutine[Any, Any, T]) -> T:
        """Execute coroutine with timeout."""
        if self.config.timeout_seconds is not None:
            try:
                return await asyncio.wait_for(coro, timeout=self.config.timeout_seconds)
            except asyncio.TimeoutError as e:
                raise AsyncExecutionError(
                    f"Async execution timed out after {self.config.timeout_seconds}s", e
                ) from None
        return await coro

    async def run(
        self, coro_or_func: Union[Coroutine[Any, Any, T], Callable[[], Coroutine[Any, Any, T]]]
    ) -> T:
        """Execute async coroutine with unified resilience patterns.

        Args:
            coro_or_func: Either a coroutine object or a callable that returns a coroutine.
                          Pass a callable to allow retrying by creating fresh coroutines.

        Returns:
            The result of the coroutine execution.

        Raises:
            AsyncExecutionError: When execution fails after all retries.
            CircuitBreakerOpenException: When circuit breaker is open.
        """
        current_task = asyncio.current_task()
        if current_task is not None:
            self.active_tasks.add(current_task)
        try:
            async with self.semaphore:
                if not self.circuit_breaker.allow_request():
                    raise AsyncExecutionError(f"Circuit breaker '{self.circuit_breaker.name}' is OPEN")

                attempt = 0
                while attempt < self.retry_policy.max_attempts:
                    try:
                        # Always create a new coroutine if callable
                        if callable(coro_or_func):
                            coro = coro_or_func()
                        else:
                            coro = coro_or_func  # Use provided coroutine as-is

                        result = await self._execute_with_timeout(coro)
                        self.original_result = result
                        self.circuit_breaker.record_success()
                        return result

                    except CircuitBreakerOpenException:
                        self.circuit_breaker.record_failure()
                        raise

                    except Exception as e:
                        is_retryable = self._is_retryable(e)
                        attempt += 1
                        self.errors.append(e)

                        if not is_retryable:
                            self.circuit_breaker.record_failure()
                            raise AsyncExecutionError(
                                "Execution failed with non-retryable error", e
                            ) from e

                        # Record failure for circuit breaker
                        self.circuit_breaker.record_failure()

                        if attempt >= self.retry_policy.max_attempts:
                            last_error = self.errors[-1] if self.errors else e
                            raise AsyncExecutionError(
                                "Execution failed after retries", last_error
                            ) from last_error

                        # Backoff and retry
                        delay = self.retry_policy.calculate_delay(attempt)
                        if delay > 0:
                            await asyncio.sleep(delay)

                raise AsyncExecutionError("Execution failed after retries")
        finally:
            if current_task is not None:
                self.active_tasks.discard(current_task)

    async def run_stream(self, aiter: AsyncIterator[T]) -> AsyncGenerator[T, None]:
        """Stream results with backpressure control."""
        async with self.semaphore:
            backpressure_sem = asyncio.Semaphore(max(1, self.config.max_concurrency // 2))
            item_counter = 0
            try:
                async for item in aiter:
                    async with backpressure_sem:
                        yield item
                        item_counter += 1
                        if item_counter % 10 == 0:
                            await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error in stream processing: {e}")
                raise
            finally:
                self._cleanup()
