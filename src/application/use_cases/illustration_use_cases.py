"""Illustration Use Cases."""

from __future__ import annotations
from dataclasses import dataclass

from src.domain.repositories.novel_repository import INovelRepository
from src.domain.value_objects.ids import NovelId
from src.application.ports.illustration_service import IIllustrationService
from src.application.dtos.illustration_dto import (
    GenerateCharacterIllustrationDTO,
    GenerateCoverIllustrationDTO,
    GenerateSceneIllustrationDTO,
    IllustrationResponseDTO,
)


@dataclass
class GenerateCharacterIllustrationUseCase:
    """Use case for generating character illustration."""

    illustration_service: IIllustrationService
    novel_repo: INovelRepository

    async def execute(self, dto: GenerateCharacterIllustrationDTO) -> IllustrationResponseDTOResponse:
        # Verify novel exists
        nid = NovelId.from_string(dto.novel_id)
        novel = await self.novel_repo.get_by_id(nid)
        if not novel:
            raise ValueError(f"Novel {dto.novel_id} not found")

        # Delegate to illustration service
        return await self.illustration_service.generate_character_illustration(dto)


@dataclass
class GenerateCoverIllustrationUseCase:
    """Use case for generating cover illustration."""

    illustration_service: IIllustrationService
    novel_repo: INovelRepository

    async def execute(self, dto: GenerateCoverIllustrationDTO) -> IllustrationResponseDTO:
        # Verify novel exists
        nid = NovelId.from_string(dto.novel_id)
        novel = await self.novel_repo.get_by_id(nid)
        if not novel:
            raise ValueError(f"Novel {dto.novel_id} not found")

        return await self.illustration_service.generate_cover_illustration(dto)


@dataclass
class GenerateSceneIllustrationUseCase:
    """Use case for generating scene illustration."""

    illustration_service: IIllustrationService
    novel_repo: INovelRepository

    async def execute(self, dto: GenerateSceneIllustrationDTO) -> IllustrationResponseDTO:
        # Verify novel exists
        nid = NovelId.from_string(dto.novel_id)
        novel = await self.novel_repo.get_by_id(nid)
        if not novel:
            raise ValueError(f"Novel {dto.novel_id} not found")

        return await self.illustration_service.generate_scene_illustration(dto)


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass
