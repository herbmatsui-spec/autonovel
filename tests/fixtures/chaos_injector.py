import random
from typing import Any


class ChaosInjector:
    """テスト中にランダムなLLM API例外（500, 429）や切断を模擬するカオス注入ヘルパー (Step 63)。"""

    def __init__(self, failure_rate: float = 0.5):
        self.failure_rate = failure_rate
        self.call_count = 0

    async def maybe_fail(self, provider_name: str) -> None:
        self.call_count += 1
        if random.random() < self.failure_rate:
            error_types = ["RateLimitError (429)", "InternalServerError (500)", "ConnectionResetError"]
            chosen = random.choice(error_types)
            raise RuntimeError(f"Chaos injected on {provider_name}: {chosen}")
