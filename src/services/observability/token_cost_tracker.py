"""
Token cost tracker for measuring LLM API usage and cost in JPY.
"""

from typing import Dict, Any
from src.config.cost_optimization import MODEL_PRICING
import logging

logger = logging.getLogger(__name__)


class TokenCostTracker:
    """
    Tracks token usage and calculates cost in Japanese Yen (JPY).
    """

    def __init__(self, usd_to_jpy_rate: float = 150.0):
        """
        Initialize the tracker with a USD to JPY conversion rate.
        Default rate is 150 JPY per 1 USD (approximate as of 2026).
        """
        self.usd_to_jpy_rate = usd_to_jpy_rate

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
    ) -> Dict[str, Any]:
        """
        Calculate the cost in USD and JPY for a given token usage.

        Args:
            model: The model identifier (e.g., "claude-3-5-sonnet")
            input_tokens: Number of input tokens (excluding cached)
            output_tokens: Number of output tokens
            cache_read_tokens: Number of tokens read from cache (input)
            cache_creation_tokens: Number of tokens written to cache (input)

        Returns:
            A dictionary with cost details:
            {
                "usd": float,
                "jpy": float,
                "breakdown": {
                    "input_usd": float,
                    "output_usd": float,
                    "cache_read_usd": float,
                    "cache_creation_usd": float,
                }
            }
        """
        # Get pricing for the model; if not found, use a default or raise
        pricing = MODEL_PRICING.get(model)
        if not pricing:
            logger.warning(f"No pricing found for model {model}. Using gemini-2.0-flash as fallback.")
            pricing = MODEL_PRICING["gemini-2.0-flash"]

        # Calculate costs in USD
        input_cost_usd = (input_tokens / 1_000_000) * pricing["input"]
        output_cost_usd = (output_tokens / 1_000_000) * pricing["output"]
        cache_read_cost_usd = (cache_read_tokens / 1_000_000) * pricing["cached_input"]
        cache_creation_cost_usd = (cache_creation_tokens / 1_000_000) * pricing["cached_input"]

        total_usd = (
            input_cost_usd
            + output_cost_usd
            + cache_read_cost_usd
            + cache_creation_cost_usd
        )

        # Convert to JPY
        total_jpy = total_usd * self.usd_to_jpy_rate

        # Calculate savings from cache (compared to if all tokens were non-cached input)
        # If we hadn't used cache, the cache_read_tokens would have been priced as regular input
        cache_savings_usd = (cache_read_tokens / 1_000_000) * (pricing["input"] - pricing["cached_input"])
        cache_savings_jpy = cache_savings_usd * self.usd_to_jpy_rate

        return {
            "usd": total_usd,
            "jpy": total_jpy,
            "breakdown": {
                "input_usd": input_cost_usd,
                "output_usd": output_cost_usd,
                "cache_read_usd": cache_read_cost_usd,
                "cache_creation_usd": cache_creation_cost_usd,
            },
            "cache_savings": {
                "usd": cache_savings_usd,
                "jpy": cache_savings_jpy,
            }
        }

    def track_request(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_creation_tokens: int = 0,
    ) -> Dict[str, Any]:
        """
        Track a single request and return the cost details.
        This method is a wrapper around calculate_cost for clarity.
        """
        return self.calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_creation_tokens=cache_creation_tokens,
        )
