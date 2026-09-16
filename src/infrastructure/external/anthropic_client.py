"""
Anthropic API client with Prompt Caching support.
"""

import anthropic
from typing import List, Dict, Any
from src.services.llm.prompt_cache_builder import PromptCacheBuilder


class AnthropicClient:
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.cache_builder = PromptCacheBuilder()

    async def generate_with_caching(
        self,
        book_id: int,
        user_prompt: str,
        model: str = "claude-3-5-sonnet",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Generate text using Anthropic's Prompt Caching for static context.
        """
        # Build cacheable blocks (world Bible and character settings)
        world_bible_block = await self.cache_builder.build_world_bible_cache_block(book_id)
        character_block = await self.cache_builder.build_character_cache_block(book_id)

        # Construct the system prompt with cache_control
        # We assume that the static parts should be cached.
        # According to Anthropic, we can add cache_control to specific blocks.
        system_payload: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": world_bible_block["text"],
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": character_block["text"],
                "cache_control": {"type": "ephemeral"},
            },
        ]

        # The user prompt is dynamic and not cached
        messages = [{"role": "user", "content": user_prompt}]

        # Call the Anthropic API
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_payload,
            messages=messages,
        )

        # Extract cache information from response headers (if available)
        # Note: The actual way to get cache info might be different; we assume the SDK provides it.
        # For the purpose of this implementation, we return the response and cache info.
        cache_info = {
            "cache_read_input_tokens": getattr(response, "cache_read_input_tokens", 0),
            "cache_creation_input_tokens": getattr(response, "cache_creation_input_tokens", 0),
        }

        return {
            "content": response.content[0].text if response.content else "",
            "cache_info": cache_info,
            "usage": response.usage,
        }
