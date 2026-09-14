"""Chapter Use Cases."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from src.domain.repositories.chapter_repository import IChapterRepository
from src.domain.repositories.novel_repository import INovelRepository
from src.domain.repositories.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import ChapterId, NovelId
from src.domain.entities.novel import Chapter
from src.application.dtos.chapter_dto import (
    CreateChapterDTO,
    UpdateChapterDTO,
    ChapterResponseDTO,
    ChapterListItemDTO,
    ReorderChaptersDTO,
)
from src.application.dtos.common import PaginationDTO, PaginatedResponseDTO


@dataclass
class CreateChapterUseCase:
    """Use case for creating a new chapter."""

    chapter_repo: IChapterRepository
    novel_repo: INovelRepository
    uow: IUnitOfWork

    async def execute(self, dto: CreateChapterDTO) -> ChapterResponseDTO:
        cid = NovelId.from_string(dto.novel_id)
        bid = NovelId.from_string(dto.branch_id)

        # Verify novel exists
        novel = await self.novel_repo.get_by_id(cid)
        if not novel:
            raise ValueError(f"Novel {dto.novel_id} not found")

        async with self.uow:
            chapter = Chapter.create(
                novel_id=cid,
                branch_id=bid,
                episode_number=dto.episode_number,
                title=dto.title,
            )
            saved = await self.chapter_repo.save(chapter)
            await self.uow.commit()
        return ChapterResponseDTO.from_entity(saved)


@dataclass
class GetChapterUseCase:
    """Use case for getting a chapter by ID."""

    chapter_repo: IChapterRepository

    async def execute(self, chapter_id: str, with_episodes: bool = False) -> Optional[ChapterResponseDTO]:
        cid = ChapterId.from_string(chapter_id)
        if with_episodes:
            chapter = await self.chapter_repo.get_by_id_with_episodes(cid)
        else:
            chapter = await self.chapter_repo.get_by_id(cid)
        return ChapterResponseDTO.from_entity(chapter) if chapter else None


@dataclass
class ListChaptersUseCase:
    """Use case for listing chapters by novel."""

    chapter_repo: IChapterRepository

    async def execute(
        self,
        novel_id: str,
        pagination: PaginationDTO,
        with_episodes: bool = False,
    ) -> PaginatedResponseDTO[ChapterListItemDTO]:
        nid = NovelId.from_string(novel_id)
        limit = pagination.limit
        offset = pagination.offset

        if with_episodes:
            chapters = await self.chapter_repo.list_by_novel_with_episodes(nid, limit, offset)
        else:
            chapters = await self.chapter_repo.list_by_novel(nid, limit, offset)

        total = await self.chapter_repo.count_by_novel(nid)
        items = [ChapterListItemDTO.from_entity(c) for c in chapters]
        return PaginatedResponseDTO(items=items, total=total, limit=limit, offset=offset)


@dataclass
class UpdateChapterUseCase:
    """Use case for updating a chapter."""

    chapter_repo: IChapterRepository
    uow: IUnitOfWork

    async def execute(self, chapter_id: str, dto: UpdateChapterDTO) -> Optional[ChapterResponseDTO]:
        cid = ChapterId.from_string(chapter_id)
        async with self.uow:
            chapter = await self.chapter_repo.get_by_id(cid)
            if not chapter:
                return None

            # Apply updates
            if dto.title is not None:
                chapter = chapter.update_content(chapter.content).update_content(chapter.content)  # Update title via content replacement pattern
                # Since Chapter is frozen, we need to create new instance
                chapter = Chapter(
                    id=chapter.id,
                    novel_id=chapter.novel_id,
                    branch_id=chapter.branch_id,
                    episode_number=chapter.episode_number,
                    title=Chapter.__annotations__['title'].__metadata__[0](dto.title) if hasattr(Chapter.__annotations__['title'], '__metadata__') else dto.title,
                    content=chapter.content,
                    score_story=chapter.score_story,
                    killer_phrase=chapter.killer_phrase,
                    summary=chapter.summary,
                    world_state=chapter.world_state,
                    trinity_review_log=chapter.trinity_review_log,
                    ai_insight=chapter.ai_insight,
                    created_at=chapter.created_at,
                    tension_delta=chapter.tension_delta,
                    qol_delta=chapter.qol_delta,
                    is_anchor=chapter.is_anchor,
                )
            if dto.content is not None:
                chapter = chapter.update_content(dto.content)
            if dto.score_story is not None:
                chapter = chapter.set_score(dto.score_story)
            if dto.killer_phrase is not None:
                chapter = Chapter(
                    id=chapter.id,
                    novel_id=chapter.novel_id,
                    branch_id=chapter.branch_id,
                    episode_number=chapter.episode_number,
                    title=chapter.title,
                    content=chapter.content,
                    score_story=chapter.score_story,
                    killer_phrase=dto.killer_phrase,
                    summary=chapter.summary,
                    world_state=chapter.world_state,
                    trinity_review_log=chapter.trinity_review_log,
                    ai_insight=chapter.ai_insight,
                    created_at=chapter.created_at,
                    tension_delta=chapter.tension_delta,
                    qol_delta=chapter.qol_delta,
                    is_anchor=chapter.is_anchor,
                )
            # Note: other fields would need similar treatment for frozen dataclass
            saved = await self.chapter_repo.save(chapter)
            await self.uow.commit()
        return ChapterResponseDTO.from_entity(saved)


@dataclass
class DeleteChapterUseCase:
    """Use case for deleting a chapter."""

    chapter_repo: IChapterRepository
    uow: IUnitOfWork

    async def execute(self, chapter_id: str) -> bool:
        cid = ChapterId.from_string(chapter_id)
        async with self.uow:
            deleted = await self.chapter_repo.delete(cid)
            if deleted:
                await self.uow.commit()
        return deleted


@dataclass
class ReorderChaptersUseCase:
    """Use case for reordering chapters."""

    chapter_repo: IChapterRepository
    uow: IUnitOfWork

    async def execute(self, novel_id: str, dto: ReorderChaptersDTO) -> bool:
        nid = NovelId.from_string(novel_id)
        orders = [(ChapterId.from_string(cid), order) for cid, order in dto.chapter_orders]
        async with self.uow:
            success = await self.chapter_repo.reorder(nid, orders)
            if success:
                await self.uow.commit()
        return success