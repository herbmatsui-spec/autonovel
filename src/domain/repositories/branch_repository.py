"""Branch repository interface."""

from __future__ import annotations
from typing import Protocol, Optional, List, runtime_checkable
from src.domain.entities.branch import Branch, BranchPlaySession
from src.domain.value_objects.ids import BranchId, NovelId
from src.domain.entities.branch import BranchPlayStatus


@runtime_checkable
class IBranchRepository(Protocol):
    """Branch repository interface."""

    async def get_by_id(self, branch_id: BranchId) -> Optional[Branch]:
        """Get branch by ID."""
        ...

    async def get_by_id_with_children(self, branch_id: BranchId) -> Optional[Branch]:
        """Get branch with children loaded."""
        ...

    async def save(self, branch: Branch) -> Branch:
        """Save branch (insert or update)."""
        ...

    async def list_by_novel(
        self,
        novel_id: NovelId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Branch]:
        """List branches by novel."""
        ...

    async def list_children(self, parent_branch_id: BranchId) -> List[Branch]:
        """List child branches of a parent."""
        ...

    async def count_by_novel(self, novel_id: NovelId) -> int:
        """Count branches in a novel."""
        ...

    async def delete(self, branch_id: BranchId) -> bool:
        """Delete branch by ID. Returns True if deleted."""
        ...

    async def exists(self, branch_id: BranchId) -> bool:
        """Check if branch exists."""
        ...

    async def get_main_branch(self, novel_id: NovelId) -> Optional[Branch]:
        """Get main branch (parent_branch_id is None)."""
        ...

    # BranchPlaySession methods
    async def get_play_session(self, session_id: BranchId) -> Optional[BranchPlaySession]:
        """Get play session by ID."""
        ...

    async def save_play_session(self, session: BranchPlaySession) -> BranchPlaySession:
        """Save play session (insert or update)."""
        ...

    async def list_play_sessions_by_branch(
        self,
        branch_id: BranchId,
        limit: int = 100,
        offset: int = 0,
        status: Optional[BranchPlayStatus] = None,
    ) -> List[BranchPlaySession]:
        """List play sessions by branch."""
        ...

    async def list_play_sessions_by_novel(
        self,
        novel_id: NovelId,
        limit: int = 100,
        offset: int = 0,
    ) -> List[BranchPlaySession]:
        """List play sessions by novel."""
        ...

    async def count_play_sessions_by_branch(
        self,
        branch_id: BranchId,
        status: Optional[BranchPlayStatus] = None,
    ) -> int:
        """Count play sessions for a branch."""
        ...

    async def delete_play_session(self, session_id: BranchId) -> bool:
        """Delete play session by ID. Returns True if deleted."""
        ...

    async def get_active_session(self, branch_id: BranchId) -> Optional[BranchPlaySession]:
        """Get active play session for branch."""
        ...