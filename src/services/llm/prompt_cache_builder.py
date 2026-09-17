"""
Prompt Cache Builder for packing static context into cache blocks.
"""

from typing import Dict, Any


class PromptCacheBuilder:
    """
    Builds cacheable prompt blocks from static context like world Bible and character settings.
    """

    def __init__(
        self,
        book_service: Any | None = None,
        character_service: Any | None = None,
    ):
        self.book_service = book_service
        self.character_service = character_service

    async def build_world_bible_cache_block(self, book_id: int) -> Dict[str, Any]:
        """
        Build a cache block for the world Bible (setting, lore, etc.).
        Returns a dictionary formatted for Anthropic's cache_control.
        """
        # Fetch the world Bible (service 未設定時は空文字フォールバック)
        if self.book_service is None:
            world_bible = ""
        else:
            world_bible = await self.book_service.get_world_bible(book_id)
        # Structure the text to meet minimum token requirements (e.g., 1024 tokens for Anthropic)
        # We'll just return the text and let the caller add cache_control
        # In practice, we might need to pad or structure to ensure it's above the threshold.
        return {
            "type": "text",
            "text": world_bible,
            # cache_control will be added by the caller (in anthropic_client.py)
        }

    async def build_character_cache_block(self, book_id: int) -> Dict[str, Any]:
        """
        Build a cache block for character settings.
        """
        # service 未設定時は空リストフォールバック
        if self.character_service is None:
            characters = []
        else:
            characters = await self.character_service.get_all_characters(book_id)
        # Format character data into a string
        char_text = "\n".join(
            [f"{char.name}: {char.description}" for char in characters]
        )
        return {
            "type": "text",
            "text": char_text,
        }

    def build_combined_cache_block(
        self, world_bible_block: Dict[str, Any], character_block: Dict[str, Any]
    ) -> list[Dict[str, Any]]:
        """
        Combine multiple static blocks into a list for the system prompt.
        The caller should add cache_control to the appropriate blocks.
        """
        return [world_bible_block, character_block]
