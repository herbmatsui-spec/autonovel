"""Writing service interface."""

from __future__ import annotations
from abc import ABC, abstractmethod

from src.application.dtos.episode_dto import WriteEpisodeDTO, RewriteEpisodeDTO
from src.application.dtos.illustration_dto import IllustrationResponseDTO


class IWritingService(ABC):
    """Interface for writing generation service."""

    @abstractmethod
    async def write_episode(
        self, dto: WriteEpisodeDTO
    ) -> str:
        """Write episode content and return the content."""
        ...

    @abstractmethod
    async def rewrite_episode(
        self, dto: RewriteEpisodeDTO
    ) -> str:
        """Rewrite episode content and return the new content."""
        ...

    # Optional: generate illustration for an episode
    @abstractmethod
    async def generate_episode_illustration(
        self, novel_id: str, episode_number: int
    ) -> IllustrationResponseDTO:
        """Generate an illustration for an episode."""
        ...
