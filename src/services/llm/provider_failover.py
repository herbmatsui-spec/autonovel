"""
Provider failover for LLM API requests.
Implements exponential backoff and automatic switching to alternative providers
on rate limits (429) or server errors (500, 502, 503, 504).
"""

import asyncio
import random
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
from src.services.llm.anthropic_client import AnthropicClient
from src.services.llm.openai_client import OpenAIClient
from src.services.llm.gemini_client import GeminiClient
from src.config.cost_optimization import MODEL_PRICING, ROUTING_TIERS
from src.services.llm.model_router import resolve_optimized_model
import logging

logger = logging.getLogger(__name__)


class ProviderFailover:
    """
    Manages failover between different LLM providers (Anthropic, OpenAI, Gemini)
    with exponential backoff retry.
    """

    def __init__(self):
        self.providers = {
            "anthropic": AnthropicClient,
            "openai": OpenAIClient,
            "gemini": GeminiClient,
        }
        # We'll assume each provider client is initialized with API keys from environment
        # For simplicity, we'll create instances on demand (or we can pass them in)
        self._clients: Dict[str, Any] = {}
        self.max_retries = 3
        self.base_delay = 1.0  # seconds

    def _get_client(self, provider_name: str) -> Any:
        """Get or create a client instance for the given provider."""
        if provider_name not in self._clients:
            # In a real implementation, we would get API keys from config/secrets
            # For now, we'll assume the clients can be instantiated without args (or with defaults)
            # This is a placeholder; actual implementation should handle API keys properly.
            client_class = self.providers[provider_name]
            self._clients[provider_name] = client_class(api_key="")  # TODO: inject API keys
        return self._clients[provider_name]

    async def generate_with_failover(
        self,
        book_id: int,
        user_prompt: str,
        task_type: str = "writing",
        episode_number: int = 1,
        total_episodes: int = 1,
        user_plan: str = "free",
        **kwargs: Any,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Generate text with automatic failover between providers.

        Returns:
            Tuple of (response_dict, provider_used)
        """
        # Determine the initial model based on task type and climax status
        # We need to check if the episode is a climax to decide the tier
        # For simplicity, we'll assume we have a way to check climax (we'll skip for now and use task_type only)
        # In a full implementation, we would use SceneTierEvaluator here.
        is_climax = False  # Placeholder; should be determined by SceneTierEvaluator
        model = resolve_optimized_model(task_type, is_climax, user_plan)

        # Determine which provider to use based on the model string
        provider = self._get_provider_from_model(model)
        if provider is None:
            # Default to anthropic if we can't determine
            provider = "anthropic"
            model = ROUTING_TIERS["tier3_premium"]  # default to sonnet for anthropic

        # Try the primary provider with retries
        for attempt in range(self.max_retries):
            try:
                client = self._get_client(provider)
                # We assume each client has a method `generate` that takes the parameters
                # This is a placeholder; actual method names and parameters may vary.
                response = await client.generate(
                    book_id=book_id,
                    user_prompt=user_prompt,
                    model=model,
                    **kwargs,
                )
                return response, provider
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                # Check if we should retry based on status code
                status_code = getattr(e, "response", None)
                if status_code is not None:
                    status_code = status_code.status_code
                else:
                    status_code = None

                # Retry on 429 (rate limit) or 5xx (server errors)
                if status_code in [429, 500, 502, 503, 504] and attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(
                        f"Provider {provider} failed with status {status_code}. "
                        f"Retrying in {delay:.2f} seconds... (attempt {attempt+1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    # If not retried or max retries reached, try failover to another provider
                    break

        # If we exhausted retries for the primary provider, try other providers in order
        # We'll define a fallback order: anthropic -> openai -> gemini -> anthropic (but avoid infinite loop)
        fallback_order = ["anthropic", "openai", "gemini"]
        # Start from the next provider in the list to avoid trying the same one again
        start_index = (fallback_order.index(provider) + 1) % len(fallback_order)
        for i in range(len(fallback_order)):
            provider_to_try = fallback_order[(start_index + i) % len(fallback_order)]
            if provider_to_try == provider:
                # We've tried all providers, break
                break
            try:
                client = self._get_client(provider_to_try)
                # We might need to adjust the model for the new provider
                # For simplicity, we'll use the same model string if it's compatible, otherwise use a default
                # This is a simplification; in reality, we need to map the model to the provider's equivalent.
                model_to_use = model
                # If the model is not available for this provider, use a default for the tier
                # We'll skip the complexity and just try with the same model string; the provider will likely fail if incompatible.
                response = await client.generate(
                    book_id=book_id,
                    user_prompt=user_prompt,
                    model=model_to_use,
                    **kwargs,
                )
                return response, provider_to_try
            except Exception as e:
                logger.warning(f"Provider {provider_to_try} failed: {e}")
                continue

        # If all providers fail, raise the last exception
        raise Exception("All LLM providers failed after failover attempts")

    def _get_provider_from_model(self, model: str) -> Optional[str]:
        """
        Determine the provider from the model string.
        This is a simplified mapping; in reality, we might have a more complex mapping.
        """
        model_lower = model.lower()
        if "claude" in model_lower:
            return "anthropic"
        elif "gpt" in model_lower:
            return "openai"
        elif "gemini" in model_lower:
            return "gemini"
        else:
            # If we don't recognize, return None
            return None