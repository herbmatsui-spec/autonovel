"""Novel Use Cases."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from src.domain.repositories.novel_repository import INovelRepository
from src.domain.repositories.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import NovelId, UserId
from src.domain.entities.novel import Novel
from src.application.dtos.novel_dto import (
    CreateNovelDTO,
    UpdateNovelDTO,
    NovelResponseDTO,
    NovelListItemDTO,
    NovelSearchDTO,
)
from src.application.dtos.common import PaginationDTO, PaginatedResponseDTO


@dataclass
class CreateNovelUseCase:
    """Use case for creating a new novel."""

    novel_repo: INovelRepository
    uow: IUnitOfWork

    async def execute(self, dto: CreateNovelDTO) -> NovelResponseDTO:
        async with self.uow:
            novel = Novel.create(
                title=dto.title,
                author_id=UserId.from_string(dto.author_id),
                genre=dto.genre,
                catchcopy=dto.catchcopy,
                synopsis=dto.synopsis,
                concept=dto.concept,
                target_episodes=dto.target_episodes,
                mode=dto.mode,
            )
            saved = await self.novel_repo.save(novel)
            await self.uow.commit()
        return NovelResponseDTO.from_entity(saved)


@dataclass
class GetNovelUseCase:
    """Use case for getting a novel by ID."""

    novel_repo: INovelRepository

    async def execute(self, novel_id: str, with_relations: bool = False) -> Optional[NovelResponseDTO]:
        nid = NovelId.from_string(novel_id)
        if with_relations:
            novel = await self.novel_repo.get_by_id_with_relations(nid)
        else:
            novel = await self.novel_repo.get_by_id(nid)
        return NovelResponseDTO.from_entity(novel) if novel else None


@dataclass
class ListNovelsUseCase:
    """Use case for listing novels with pagination and filters."""

    novel_repo: INovelRepository

    async def execute(
        self,
        pagination: PaginationDTO,
        search: Optional[NovelSearchDTO] = None,
    ) -> PaginatedResponseDTO[NovelListItemDTO]:
        limit = pagination.limit
        offset = pagination.offset

        if search and search.title_contains:
            novels = await self.novel_repo.search_by_title(search.title_contains, limit, offset)
            total = len(novels)  # Approximate
        else:
            status = search.status if search else None
            mode = search.mode if search else None
            author_id = search.author_id if search else None
            novels = await self.novel_repo.list_all(limit, offset, status, mode, author_id)
            total = await self.novel_repo.count(status, mode, author_id)

        items = [NovelListItemDTO.from_entity(n) for n in novels]
        return PaginatedResponseDTO(items=items, total=total, limit=limit, offset=offset)


@dataclass
class UpdateNovelUseCase:
    """Use case for updating a novel."""

    novel_repo: INovelRepository
    uow: IUnitOfWork

    async def execute(self, novel_id: str, dto: UpdateNovelDTO) -> Optional[NovelResponseDTO]:
        nid = NovelId.from_string(novel_id)
        async with self.uow:
            novel = await self.novel_repo.get_by_id(nid)
            if not novel:
                return None

            novel.update_metadata(
                title=dto.title,
                genre=dto.genre,
                catchcopy=dto.catchcopy,
                synopsis=dto.synopsis,
                concept=dto.concept,
                target_episodes=dto.target_episodes,
                style_dna=dto.style_dna,
            )
            saved = await self.novel_repo.save(novel)
            await self.uow.commit()
        return NovelResponseDTO.from_entity(saved)


@dataclass
class DeleteNovelUseCase:
    """Use case for deleting a novel."""

    novel_repo: INovelRepository
    uow: IUnitOfWork

    async def execute(self, novel_id: str) -> bool:
        nid = NovelId.from_string(novel_id)
        async with self.uow:
            deleted = await self.novel_repo.delete(nid)
            if deleted:
                await self.uow.commit()
        return deleted


@dataclass
class ChangeNovelStatusUseCase:
    """Use case for changing novel status."""

    novel_repo: INovelRepository
    uow: IUnitOfWork

    async def execute(self, novel_id: str, status: "NovelStatus") -> bool:
        from src.domain.value_objects.metadata import NovelStatus
        nid = NovelId.from_string(novel_id)
        async with self.uow:
            updated = await self.novel_repo.update_status(nid, status)
            if updated:
                await self.uow.commit()
        return updated


@dataclass
class SetNovelModeUseCase:
    """Use case for setting novel writing mode."""

    novel_repo: INovelRepository
    uow: IUnitOfWork

    async def execute(self, novel_id: str, mode: "NovelMode") -> bool:
        from src.domain.value_objects.metadata import NovelMode
        nid = NovelId.from_string(novel_id)
        async with self.uow:
            updated = await self.novel_repo.update_mode(nid, mode)
            if updated:
                await self.uow.commit()
        return updated


@dataclass
class AddNovelCostUseCase:
    """Use case for adding cost to a novel."""

    novel_repo: INovelRepository
    uow: IUnitOfWork

    async def execute(self, novel_id: str, cost: float, tokens: int) -> bool:
        nid = NovelId.from_string(novel_id)
        async with self.uow:
            updated = await self.novel_repo.add_cost(nid, cost, tokens)
            if updated:
                await self.uow.commit()
        return updated


@dataclass
class GetLatestNovelsUseCase:
    """Use case for getting latest updated novels."""

    novel_repo: INovelRepository

    async def execute(self, limit: int = 10, author_id: Optional[str] = None) -> list[NovelListItemDTO]:
        novels = await self.novel_repo.get_latest_updated(limit, author_id)
        return [NovelListItemDTO.from_entity(n) for n in novels]


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.domain.value_objects.metadata import NovelStatus, NovelMode