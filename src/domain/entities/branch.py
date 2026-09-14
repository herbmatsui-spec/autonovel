"""Branch domain entity."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4
from enum import Enum
import json

from src.domain.value_objects.ids import NovelId, BranchId
from src.domain.value_objects.metadata import BranchMetadata


class BranchPlayStatus(Enum):
    """Branch play session status."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass
class Branch:
    """Branch entity - alternate storyline path."""
    id: BranchId
    novel_id: NovelId
    name: str
    parent_branch_id: Optional[BranchId] = None
    fork_episode: int = 0
    graph_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Child branches
    _children: List[Branch] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Branch name cannot be empty")
        if self.fork_episode < 0:
            raise ValueError("Fork episode cannot be negative")

    @classmethod
    def create(
        cls,
        novel_id: NovelId,
        name: str,
        parent_branch_id: Optional[BranchId] = None,
        fork_episode: int = 0,
    ) -> Branch:
        """Factory method to create a new branch."""
        branch_id = BranchId.generate()
        now = datetime.now()
        return cls(
            id=branch_id,
            novel_id=novel_id,
            name=name,
            parent_branch_id=parent_branch_id,
            fork_episode=fork_episode,
            graph_data={},
            created_at=now,
            updated_at=now,
        )

    @classmethod
    def create_main_branch(cls, novel_id: NovelId) -> Branch:
        """Create the main/default branch."""
        return cls(
            id=BranchId.generate(),
            novel_id=novel_id,
            name="Main",
            parent_branch_id=None,
            fork_episode=0,
            graph_data={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def update_name(self, name: str) -> None:
        """Update branch name."""
        if not name.strip():
            raise ValueError("Branch name cannot be empty")
        self.name = name
        self.updated_at = datetime.now()

    def update_graph(self, graph_data: Dict[str, Any]) -> None:
        """Update branch graph data."""
        self.graph_data = graph_data
        self.updated_at = datetime.now()

    def add_child(self, child: Branch) -> None:
        """Add a child branch."""
        if child.parent_branch_id != self.id:
            raise ValueError("Child's parent_branch_id must match this branch")
        if child.novel_id != self.novel_id:
            raise ValueError("Child must belong to same novel")
        self._children.append(child)

    def get_children(self) -> List[Branch]:
        """Get child branches."""
        return list(self._children)

    def is_main_branch(self) -> bool:
        """Check if this is the main branch."""
        return self.parent_branch_id is None

    def get_depth(self) -> int:
        """Get branch depth from main."""
        depth = 0
        current = self
        while current.parent_branch_id is not None:
            depth += 1
            # In real implementation, would fetch parent from repository
            break
        return depth

    def to_metadata(self) -> BranchMetadata:
        """Convert to metadata value object."""
        return BranchMetadata(
            branch_id=NovelId(self.id.value),
            novel_id=self.novel_id,
            name=self.name,
            parent_branch_id=NovelId(self.parent_branch_id.value) if self.parent_branch_id else None,
            fork_episode=self.fork_episode,
            graph_data=json.dumps(self.graph_data, ensure_ascii=False),
            created_at=self.created_at,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Branch):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class BranchPlaySession:
    """Interactive Fiction branch play session."""
    id: BranchId  # Using BranchId as generic UUID
    novel_id: NovelId
    branch_id: BranchId
    current_node_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    save_points: Dict[str, Any] = field(default_factory=dict)
    status: BranchPlayStatus = BranchPlayStatus.ACTIVE
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.version < 1:
            self.version = 1

    @classmethod
    def create(
        cls,
        novel_id: NovelId,
        branch_id: BranchId,
        initial_node_id: Optional[str] = None,
    ) -> BranchPlaySession:
        """Factory method to create a new play session."""
        session_id = BranchId.generate()
        now = datetime.now()
        return cls(
            id=session_id,
            novel_id=novel_id,
            branch_id=branch_id,
            current_node_id=initial_node_id,
            context={},
            save_points={},
            status=BranchPlayStatus.ACTIVE,
            version=1,
            created_at=now,
            updated_at=now,
        )

    def update_node(self, node_id: str) -> None:
        """Update current node."""
        self.current_node_id = node_id
        self.updated_at = datetime.now()

    def update_context(self, context: Dict[str, Any]) -> None:
        """Update session context."""
        self.context = context
        self.updated_at = datetime.now()

    def add_save_point(self, name: str, data: Dict[str, Any]) -> None:
        """Add a save point."""
        self.save_points[name] = data
        self.updated_at = datetime.now()

    def get_save_point(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a save point."""
        return self.save_points.get(name)

    def pause(self) -> None:
        """Pause the session."""
        self.status = BranchPlayStatus.PAUSED
        self.updated_at = datetime.now()

    def resume(self) -> None:
        """Resume the session."""
        self.status = BranchPlayStatus.ACTIVE
        self.updated_at = datetime.now()

    def complete(self) -> None:
        """Mark session as completed."""
        self.status = BranchPlayStatus.COMPLETED
        self.updated_at = datetime.now()

    def abandon(self) -> None:
        """Abandon the session."""
        self.status = BranchPlayStatus.ABANDONED
        self.updated_at = datetime.now()

    def increment_version(self) -> None:
        """Increment session version (for optimistic locking)."""
        self.version += 1
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "novel_id": str(self.novel_id),
            "branch_id": str(self.branch_id),
            "current_node_id": self.current_node_id,
            "context": self.context,
            "save_points": self.save_points,
            "status": self.status.value,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BranchPlaySession):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


__all__ = [
    "Branch",
    "BranchPlaySession",
    "BranchPlayStatus",
]