"""Branch Use Cases."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID

from src.domain.repositories.branch_repository import IBranchRepository
from src.domain.repositories.novel_repository import INovelRepository
from src.domain.repositories.unit_of_work import IUnitOfWork
from src.domain.value_objects.ids import NovelId, BranchId
from src.domain.entities.branch import Branch
from src.application.dtos.branch_dto import (
    CreateBranchDTO,
    UpdateBranchDTO,
    BranchResponseDTO,
    BranchListItemDTO,
)
from src.application.dtos.common import PaginationDTO, PaginatedResponseDTO


@dataclass
class CreateBranchUseCase:
    """Use case for creating a new branch."""

    branch_repo: IBranchRepository
    novel_repo: INovelRepository
    uow: IUnitOfWork

    async def execute(self, dto: CreateBranchDTO) -> BranchResponseDTO:
        nid = NovelId.from_string(dto.novel_id)
        # Verify novel exists
        novel = await self.novel_repo.get_by_id(nid)
        if not novel:
            raise ValueError(f"Novel {dto.novel_id} not found")

        parent_bid = None
        if dto.parent_branch_id:
            parent_bid = BranchId.from_string(dto.parent_branch_id)
            # TODO: Verify parent branch exists and belongs to same novel

        async with self.uow:
            branch = Branch.create(
                novel_id=nid,
                name=dto.name,
                parent_branch_id=parent_bid,
                fork_episode=dto.fork_episode,
            )
            saved = await self.branch_repo.save(branch)
            await self.uow.commit()
        return BranchResponseDTO.from_entity(saved)


@dataclass
class GetBranchUseCase:
    """Use case for getting a branch by ID."""

    branch_repo: IBranchRepository

    async def execute(self, branch_id: str) -> Optional[BranchResponseDTO]:
        bid = BranchId.from_string(branch_id)
        branch = await self.branch_repo.get_by_id(bid)
        return BranchResponseDTO.from_entity(branch) if branch else None


@dataclass
class ListBranchesUseCase:
    """Use case for listing branches by novel."""

    branch_repo: IBranchRepository

    async def execute(
        self,
        novel_id: str,
        pagination: PaginationDTO,
    ) -> PaginatedResponseDTO[BranchListItemDTO]:
        nid = NovelId.from_string(novel_id)
        limit = pagination.limit
        offset = pagination.offset

        branches = await self.branch_repo.list_by_novel(nid, limit, offset)
        total = await self.branch_repo.count_by_novel(nid)

        items = [BranchListItemDTO.from_entity(b) for b in branches]
        return PaginatedResponseDTO(items=items, total=total, limit=limit, offset=offset)


@dataclass
class UpdateBranchUseCase:
    """Use case for updating a branch."""

    branch_repo: IBranchRepository
    uow: IUnitOfWork

    async def execute(self, branch_id: str, dto: UpdateBranchDTO) -> Optional[BranchResponseDTO]:
        bid = BranchId.from_string(branch_id)
        async with self.uow:
            branch = await self.branch_repo.get_by_id(bid)
            if not branch:
                return None

            if dto.name is not None:
                branch.update_name(dto.name)
            if dto.graph_data is not None:
                branch.update_graph(dto.graph_data)
            # Note: other fields like novel_id, parent_branch_id, fork_episode are immutable after creation

            saved = await self.branch_repo.save(branch)
            await self.uow.commit()
        return BranchResponseDTO.from_entity(saved)


@dataclass
class DeleteBranchUseCase:
    """Use case for deleting a branch."""

    branch_repo: IBranchRepository
    uow: IUnitOfWork

    async def execute(self, branch_id: str) -> bool:
        bid = BranchId.from_string(branch_id)
        async with self.uow:
            deleted = await self.branch_repo.delete(bid)
            if deleted:
                await self.uow.commit()
        return deleted


@dataclass
class CreateBranchPlaySessionUseCase:
    """Use case for creating a branch play session."""

    branch_repo: IBranchRepository
    # We might need a repository for play sessions, but we don't have one yet.
    # For now, we'll just validate the branch and return a DTO without persisting.
    # In a full implementation, we would have IBranchPlaySessionRepository.
    novel_repo: INovelRepository

    async def execute(self, novel_id: str, branch_id: str, initial_node_id: Optional[str] = None) -> dict:
        # TODO: Implement with proper repository
        # For now, return a mock response
        return {
            "id": "mock-session-id",
            "novel_id": novel_id,
            "branch_id": branch_id,
            "current_node_id": initial_node_id,
            "status": "active",
            "version": 1,
            "created_at": "2026-09-12T11:00:00Z",
            "updated_at": "2026-09-12T11:00:00Z",
        }


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass