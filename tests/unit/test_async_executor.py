"""Tests for AsyncExecutor core functionality."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.async_executor import (
    AsyncExecutor,
    AsyncExecutorConfig,
    AsyncExecutionError,
)
from src.shared.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitState


class TestAsyncExecutorSuccess:
    """Tests for successful execution scenarios."""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Test that successful coroutine returns result."""
        config = AsyncExecutorConfig(max_retries=3)
        executor = AsyncExecutor(config)

        async def successful_task():
            await asyncio.sleep(0.01)
            return "success"

        result = await executor.run(successful_task())
        assert result == "success"
        assert executor.original_result == "success"

    @pytest.mark.asyncio
    async def test_success_with_context_manager(self):
        """Test execution using async context manager."""
        config = AsyncExecutorConfig(max_retries=3)
        async with AsyncExecutor(config) as executor:
            async def successful_task():
                return "context_success"

            result = await executor.run(successful_task())
            assert result == "context_success"


class TestAsyncExecutorRetry:
    """Tests for retry logic."""

    @pytest.mark.asyncio
    async def test_retry_then_success(self):
        """Test that transient failures are retried and eventually succeed."""
        config = AsyncExecutorConfig(max_retries=3, base_delay=0.01, jitter=False)
        executor = AsyncExecutor(config)

        call_count = 0

        async def flaky_task():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise asyncio.TimeoutError("Temporary failure")
            return "retry_success"

        # Pass a callable to ensure fresh coroutine each retry
        result = await executor.run(flaky_task)
        assert result == "retry_success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted_raises_error(self):
        """Test that AsyncExecutionError is raised after max retries exhausted."""
        config = AsyncExecutorConfig(max_retries=2, base_delay=0.01, jitter=False)
        executor = AsyncExecutor(config)

        async def always_fails():
            raise asyncio.TimeoutError("Persistent failure")

        with pytest.raises(AsyncExecutionError) as exc_info:
            await executor.run(always_fails)

        assert "Execution failed after retries" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_non_retryable_error_raises_immediately(self):
        """Test that non-retryable errors are raised immediately without retries."""
        config = AsyncExecutorConfig(max_retries=3, base_delay=0.01)
        executor = AsyncExecutor(config)

        call_count = 0

        async def non_retryable_task():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")

        with pytest.raises(AsyncExecutionError) as exc_info:
            await executor.run(non_retryable_task())

        assert "non-retryable error" in str(exc_info.value).lower()
        assert call_count == 1


class TestAsyncExecutorTimeout:
    """Tests for timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_raises_error(self):
        """Test that timeout raises AsyncExecutionError."""
        config = AsyncExecutorConfig(timeout_seconds=0.05, max_retries=1, base_delay=0.01)
        executor = AsyncExecutor(config)

        async def slow_task():
            await asyncio.sleep(0.2)
            return "too_slow"

        with pytest.raises(AsyncExecutionError) as exc_info:
            await executor.run(slow_task)

        assert "Execution failed after retries" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_retries_then_succeeds(self):
        """Test that timeout on first attempt retries and can succeed."""
        config = AsyncExecutorConfig(timeout_seconds=0.05, max_retries=3, base_delay=0.01, jitter=False)
        executor = AsyncExecutor(config)

        call_count = 0

        async def sometimes_slow():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                await asyncio.sleep(0.2)  # First call times out
            return "success_after_retry"

        result = await executor.run(sometimes_slow)
        assert result == "success_after_retry"
        assert call_count == 2


class TestAsyncExecutorCircuitBreaker:
    """Tests for circuit breaker integration."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_open_blocks_execution(self):
        """Test that open circuit breaker blocks execution immediately."""
        import time
        cb_config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=60.0)
        config = AsyncExecutorConfig(circuit_breaker_config=cb_config)
        executor = AsyncExecutor(config)

        # Open circuit breaker by recording a failure
        executor.circuit_breaker.record_failure()
        assert executor.circuit_breaker.state == CircuitState.OPEN

        with pytest.raises(AsyncExecutionError) as exc_info:
            await executor.run(asyncio.sleep(0.01))

        assert "circuit breaker" in str(exc_info.value).lower()
        assert "open" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_failure_on_error(self):
        """Test that circuit breaker records failures."""
        cb_config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60.0)
        config = AsyncExecutorConfig(circuit_breaker_config=cb_config, max_retries=1, base_delay=0.01)
        executor = AsyncExecutor(config)

        async def failing_task():
            raise asyncio.TimeoutError("Failure")

        with pytest.raises(AsyncExecutionError):
            await executor.run(failing_task())

        assert executor.circuit_breaker.failure_count == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self):
        """Test that circuit breaker opens after reaching failure threshold."""
        cb_config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60.0)
        config = AsyncExecutorConfig(circuit_breaker_config=cb_config, max_retries=1, base_delay=0.01)
        executor = AsyncExecutor(config)

        async def failing_task():
            raise asyncio.TimeoutError("Failure")

        # First failure
        with pytest.raises(AsyncExecutionError):
            await executor.run(failing_task())

        assert executor.circuit_breaker.state == CircuitState.CLOSED

        # Second failure - should open circuit breaker
        with pytest.raises(AsyncExecutionError):
            await executor.run(failing_task())

        assert executor.circuit_breaker.state == CircuitState.OPEN

        # Third attempt should be blocked immediately
        with pytest.raises(AsyncExecutionError) as exc_info:
            await executor.run(failing_task())

        assert "circuit breaker" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_allows_request(self):
        """Test that half-open state allows test requests."""
        cb_config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.01)
        config = AsyncExecutorConfig(circuit_breaker_config=cb_config, max_retries=1, base_delay=0.01)
        executor = AsyncExecutor(config)

        # Fail once to open circuit breaker
        async def failing_task():
            raise asyncio.TimeoutError("Failure")

        with pytest.raises(AsyncExecutionError):
            await executor.run(failing_task())

        assert executor.circuit_breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.02)

        # Now should be half-open and allow request
        async def successful_task():
            return "success"

        result = await executor.run(successful_task())
        assert result == "success"
        # After success in half-open, should close
        assert executor.circuit_breaker.state == CircuitState.CLOSED


class TestAsyncExecutorConcurrency:
    """Tests for semaphore-based concurrency control."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Test that semaphore limits concurrent executions."""
        config = AsyncExecutorConfig(max_concurrency=2)
        executor = AsyncExecutor(config)

        running = 0
        max_running = 0
        lock = asyncio.Lock()

        async def limited_task():
            nonlocal running, max_running
            async with lock:
                running += 1
                max_running = max(max_running, running)
            await asyncio.sleep(0.05)
            async with lock:
                running -= 1

        # Run 5 tasks concurrently
        tasks = [executor.run(limited_task()) for _ in range(5)]
        await asyncio.gather(*tasks)

        assert max_running <= 2

    @pytest.mark.asyncio
    async def test_context_manager_concurrency(self):
        """Test concurrency control with context manager."""
        config = AsyncExecutorConfig(max_concurrency=1)
        max_running = 0
        running = 0

        async with AsyncExecutor(config) as executor:
            async def task():
                nonlocal running, max_running
                running += 1
                max_running = max(max_running, running)
                await asyncio.sleep(0.02)
                running -= 1

            await asyncio.gather(executor.run(task()), executor.run(task()))

        assert max_running <= 1


class TestAsyncExecutorStream:
    """Tests for streaming with backpressure."""

    @pytest.mark.asyncio
    async def test_stream_yields_items(self):
        """Test that run_stream yields items from async iterator."""
        config = AsyncExecutorConfig(max_concurrency=2)
        executor = AsyncExecutor(config)

        async def item_generator():
            for i in range(5):
                yield i
                await asyncio.sleep(0.01)

        items = []
        async for item in executor.run_stream(item_generator()):
            items.append(item)

        assert items == [0, 1, 2, 3, 4]

    @pytest.mark.asyncio
    async def test_stream_backpressure_semaphore(self):
        """Test that backpressure semaphore limits concurrent yields."""
        config = AsyncExecutorConfig(max_concurrency=2)
        executor = AsyncExecutor(config)

        async def slow_generator():
            for i in range(3):
                await asyncio.sleep(0.02)
                yield i

        start = asyncio.get_event_loop().time()
        items = []
        async for item in executor.run_stream(slow_generator()):
            items.append(item)
        elapsed = asyncio.get_event_loop().time() - start

        # Should take at least 3 * 0.02 = 0.06 seconds
        assert elapsed >= 0.05
        assert items == [0, 1, 2]

    @pytest.mark.asyncio
    async def test_stream_propagates_exception(self):
        """Test that exceptions in stream are propagated."""
        config = AsyncExecutorConfig()
        executor = AsyncExecutor(config)

        async def failing_generator():
            yield 1
            yield 2
            raise ValueError("Stream error")

        with pytest.raises(ValueError):
            async for _ in executor.run_stream(failing_generator()):
                pass


class TestAsyncExecutorErrorHandling:
    """Tests for error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_cleanup_on_exception(self):
        """Test that cleanup happens on exception."""
        config = AsyncExecutorConfig()
        executor = AsyncExecutor(config)

        async def failing_task():
            raise ValueError("Test error")

        with pytest.raises(AsyncExecutionError):
            await executor.run(failing_task())

        # Verify errors list captures the exception
        assert len(executor.errors) == 1
        assert isinstance(executor.errors[0], ValueError)

    @pytest.mark.asyncio
    async def test_multiple_errors_collected(self):
        """Test that multiple errors are collected during retries."""
        config = AsyncExecutorConfig(max_retries=3, base_delay=0.01, jitter=False)
        executor = AsyncExecutor(config)

        call_count = 0

        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise asyncio.TimeoutError(f"Attempt {call_count}")

        with pytest.raises(AsyncExecutionError):
            await executor.run(always_fails())

        assert len(executor.errors) == 3  # 3 retry attempts

    @pytest.mark.asyncio
    async def test_retryable_status_code(self):
        """Test that HTTP status codes are checked for retryability."""
        config = AsyncExecutorConfig(max_retries=2, base_delay=0.01, jitter=False)
        executor = AsyncExecutor(config)

        # Create a mock exception with status_code
        class MockHTTPError(Exception):
            def __init__(self, status_code):
                self.status_code = status_code

        call_count = 0

        async def http_error_task():
            nonlocal call_count
            call_count += 1
            raise MockHTTPError(503)  # Retryable status code

        with pytest.raises(AsyncExecutionError):
            await executor.run(http_error_task())

        assert call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_non_retryable_status_code(self):
        """Test that non-retryable HTTP status codes don't retry."""
        config = AsyncExecutorConfig(max_retries=2, base_delay=0.01)
        executor = AsyncExecutor(config)

        class MockHTTPError(Exception):
            def __init__(self, status_code):
                self.status_code = status_code

        call_count = 0

        async def http_404_task():
            nonlocal call_count
            call_count += 1
            raise MockHTTPError(404)  # Non-retryable

        with pytest.raises(AsyncExecutionError):
            await executor.run(http_404_task())

        assert call_count == 1  # Should not retry


# Integration tests
class TestAsyncExecutorIntegration:
    """Integration-style tests."""

    @pytest.mark.asyncio
    async def test_full_workflow_with_retries_and_circuit_breaker(self):
        """Test a realistic workflow with retries and circuit breaker."""
        cb_config = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=1.0)
        config = AsyncExecutorConfig(
            max_retries=3,
            base_delay=0.01,
            jitter=False,
            timeout_seconds=0.5,
            circuit_breaker_config=cb_config,
        )
        executor = AsyncExecutor(config)

        call_count = 0

        async def unreliable_service():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise asyncio.TimeoutError("Transient failure")
            return "success"

        result = await executor.run(unreliable_service())
        assert result == "success"
        assert call_count == 3
        assert executor.circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_concurrent_executions_share_circuit_breaker(self):
        """Test that concurrent executions share the same circuit breaker state."""
        cb_config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1.0)
        config = AsyncExecutorConfig(
            max_retries=1,
            base_delay=0.01,
            circuit_breaker_config=cb_config,
        )
        executor = AsyncExecutor(config)

        async def failing_task():
            raise asyncio.TimeoutError("Failure")

        # Run multiple failing tasks concurrently
        tasks = [executor.run(failing_task()) for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should fail
        assert all(isinstance(r, AsyncExecutionError) for r in results)

        # Circuit breaker should have recorded all failures
        assert executor.circuit_breaker.failure_count >= 3

    @pytest.mark.asyncio
    async def test_context_manager_cancels_tasks_on_exit(self):
        """Test that context manager cancels tasks on exception."""
        config = AsyncExecutorConfig(max_concurrency=1)
        cancelled = False

        async with AsyncExecutor(config) as executor:
            async def long_task():
                try:
                    await asyncio.sleep(10)
                except asyncio.CancelledError:
                    nonlocal cancelled
                    cancelled = True
                    raise

            # Start a long-running task
            task = asyncio.create_task(executor.run(long_task()))
            # Don't wait for it, just exit context
            await asyncio.sleep(0.01)

        # Task should be cancelled on context exit
        assert cancelled


if __name__ == "__main__":
    pytest.main([__file__, "-v"])