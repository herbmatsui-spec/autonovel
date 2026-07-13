import asyncio
import logging
from typing import Any, Optional

import httpx

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from .retry_policy import RetryPolicy

logger = logging.getLogger(__name__)

class CircuitBreakerOpenException(Exception):
    """Exception raised when the circuit breaker is in OPEN state."""
    pass

class ResilientHttpClient:
    """
    A resilient HTTP client that integrates retry logic and circuit breaking.
    """
    def __init__(
        self,
        name: str,
        retry_policy: RetryPolicy = RetryPolicy(),
        cb_config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.retry_policy = retry_policy
        self.circuit_breaker = CircuitBreaker(name, cb_config or CircuitBreakerConfig())
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0))

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any
    ) -> httpx.Response:
        """
        Executes an HTTP request with resilience patterns.
        """
        last_exception = None

        for attempt in range(self.retry_policy.max_attempts):
            # 1. Circuit Breaker Check
            if not self.circuit_breaker.allow_request():
                logger.error(f"[{self.name}] Circuit breaker is OPEN. Request blocked.")
                raise CircuitBreakerOpenException(f"Circuit breaker '{self.name}' is OPEN")

            try:
                # 2. Execute Request
                response = await self.client.request(method, url, **kwargs)

                # 3. Handle Response
                if response.status_code in self.retry_policy.retryable_status_codes:
                    # Trigger retry logic for specific status codes
                    raise httpx.HTTPStatusError(
                        f"Retryable status code: {response.status_code}",
                        request=response.request,
                        response=response
                    )

                # Success: Record and return
                self.circuit_breaker.record_success()
                return response

            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exception = e
                self.circuit_breaker.record_failure()

                # Check if we should retry
                if attempt < self.retry_policy.max_attempts - 1:
                    delay = self.retry_policy.calculate_delay(attempt)
                    logger.warning(
                        f"[{self.name}] Request failed ({type(e).__name__}). "
                        f"Retrying in {delay:.2f}s... (Attempt {attempt + 1}/{self.retry_policy.max_attempts})"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[{self.name}] All retry attempts failed. Final error: {e}")

        if last_exception:
            raise last_exception
        raise Exception("Request failed without a specific exception")

    async def close(self):
        """Closes the underlying HTTP client."""
        await self.client.aclose()

    # Convenience methods
    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)
