"""Illustration service interface."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

from src.application.dtos.illustration_dto import (
    GenerateCharacterIllustrationDTO,
    GenerateCoverIllustrationDTO,
    GenerateSceneIllustrationDTO,
    IllustrationResponseDTO,
)


class IIllustrationService(ABC):
    """Interface for illustration generation service."""

    @abstractmethod
    async def generate_character_illustration(
        self, dto: GenerateCharacterIllustrationDTO
    ) -> IllustrationResponseDTO:
        """Generate an illustration for a character."""
        ...

    @abstractmethod
    async def generate_cover_illustration(
        self, dto: GenerateCoverIllustrationDTO
    ) -> IllustrationResponseDTO:
        """Generate an illustration for a book cover."""
        ...

    @abstractmethod
    async def generate_scene_illustration(
        self, dto: GenerateSceneIllustrationDTO
    ) -> IllustrationResponseDTO:
        """Generate an illustration for a scene."""
        ...