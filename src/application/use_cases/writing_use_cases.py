"""Writing Use Cases."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

from src.domain.repositories.episode_repository import IEpisodeRepository
from src.domain.repositories.novel_repository import INovelRepository
from src.domain.repositories.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import NovelId, EpisodeId, ChapterId
from src.domain.value_objects.text import Title
from src.domain.entities.novel import Episode
from src.application.dtos.episode_dto import (
    WriteEpisodeDTO,
    RewriteEpisodeDTO,
    EpisodeResponseDTO,
    EpisodeListItemDTO,
    ExpandPlotDTO,
)
from src.application.dtos.common import PaginationDTO, PaginatedResponseDTO
from src.application.ports.writing_service import IWritingService


@dataclass
class WriteEpisodeUseCase:
    """Use case for writing a new episode."""

    episode_repo: IEpisodeRepository
    novel_repo: INovelRepository
    uow: IUnitOfWork
    writing_service: IWritingService

    async def execute(self, dto: WriteEpisodeDTO) -> EpisodeResponseDTO:
        # Verify novel exists
        nid = NovelId.from_string(dto.novel_id)
        novel = await self.novel_repo.get_by_id(nid)
        if not novel:
            raise ValueError(f"Novel {dto.novel_id} not found")

        # Verify chapter exists? We don't have chapter repository injected.
        # We could inject chapter repository, but for now we'll skip.
        # The chapter_id is used to group episodes under a chapter.
        cid = ChapterId.from_string(dto.chapter_id)

        # Get the next episode number for this chapter
        async with self.uow:
            episode_number = await self.episode_repo.get_max_episode_number(cid) + 1
            # Create episode with placeholder content
            episode = Episode(
                id=NovelId.generate(),
                novel_id=nid,
                branch_id=NovelId.from_string(dto.branch_id),  # Using NovelId as generic UUID for branch_id
                number=episode_number,
                title=Title(dto.title),
                content="",  # Placeholder, will be filled by writing service
                plot_summary=dto.plot_summary,
                tension=dto.target_tension,
                catharsis=dto.target_catharsis,
                status="planned",
                created_at=datetime.now(),
            )
            # Generate content using writing service
            generated_content = await self.writing_service.write_episode(dto)
            # Update episode with generated content (since Episode is immutable, create new instance)
            episode = Episode(
                id=episode.id,
                novel_id=episode.novel_id,
                branch_id=episode.branch_id,
                number=episode.number,
                title=episode.title,
                content=generated_content,
                plot_summary=episode.plot_summary,
                tension=episode.tension,
                catharsis=episode.catharsis,
                status=episode.status,
                created_at=episode.created_at,
            )
            saved = await self.episode_repo.save(episode)
            await self.uow.commit()
        return EpisodeResponseDTO.from_entity(saved)


@dataclass
class RewriteEpisodeUseCase:
    """Use case for rewriting an episode."""

    episode_repo: IEpisodeRepository
    uow: IUnitOfWork
    writing_service: IWritingService

    async def execute(self, dto: RewriteEpisodeDTO) -> Optional[EpisodeResponseDTO]:
        eid = EpisodeId.from_string(dto.episode_id)
        async with self.uow:
            episode = await self.episode_repo.get_by_id(eid)
            if not episode:
                return None

            # Generate rewritten content using writing service
            generated_content = await self.writing_service.rewrite_episode(dto)
            # Update episode with generated content
            updated_episode = Episode(
                id=episode.id,
                novel_id=episode.novel_id,
                branch_id=episode.branch_id,
                number=episode.number,
                title=episode.title,
                content=generated_content,
                plot_summary=episode.plot_summary,
                tension=dto.target_tension if dto.target_tension is not None else episode.tension,
                catharsis=dto.target_catharsis if dto.target_catharsis is not None else episode.catharsis,
                status=episode.status,
                created_at=episode.created_at,
            )
            saved = await self.episode_repo.save(updated_episode)
            await self.uow.commit()
        return EpisodeResponseDTO.from_entity(saved)


@dataclass
class GetEpisodeUseCase:
    """Use case for getting an episode by ID."""

    episode_repo: IEpisodeRepository

    async def execute(self, episode_id: str) -> Optional[EpisodeResponseDTO]:
        eid = EpisodeId.from_string(episode_id)
        episode = await self.episode_repo.get_by_id(eid)
        return EpisodeResponseDTO.from_entity(episode) if episode else None


@dataclass
class ListEpisodesUseCase:
    """Use case for listing episodes by chapter."""

    episode_repo: IEpisodeRepository

    async def execute(
        self,
        chapter_id: str,
        pagination: PaginationDTO,
    ) -> PaginatedResponseDTO[EpisodeListItemDTO]:
        cid = ChapterId.from_string(chapter_id)
        limit = pagination.limit
        offset = pagination.offset

        episodes = await self.episode_repo.list_by_chapter(cid, limit, offset)
        total = await self.episode_repo.count_by_chapter(cid)

        items = [EpisodeListItemDTO.from_entity(e) for e in episodes]
        return PaginatedResponseDTO(items=items, total=total, limit=limit, offset=offset)


@dataclass
class DeleteEpisodeUseCase:
    """Use case for deleting an episode."""

    episode_repo: IEpisodeRepository
    uow: IUnitOfWork

    async def execute(self, episode_id: str) -> bool:
        eid = EpisodeId.from_string(episode_id)
        async with self.uow:
            deleted = await self.episode_repo.delete(eid)
            if deleted:
                await self.uow.commit()
        return deleted


@dataclass
class ExpandPlotIntoEpisodeUseCase:
    """Use case for expanding a plot point into an episode."""

    episode_repo: IEpisodeRepository
    novel_repo: INovelRepository
    uow: IUnitOfWork

    async def execute(self, dto: ExpandPlotDTO) -> EpisodeResponseDTO:
        raise NotImplementedError(
            "ExpandPlotIntoEpisodeUseCase は未実装です。Plotドメインサービス連携後に有効化してください。"
        )


# 後方互換性・別名
ExpandPlotUseCase = ExpandPlotIntoEpisodeUseCase


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass
