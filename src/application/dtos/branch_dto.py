"""Branch DTOs."""

from __future__ import annotations
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.branch import Branch, BranchPlaySession
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

MODEL_CONFIG_DEFAULTS = ConfigDict(populate_by_name=True, extra="allow", protected_namespaces=())


class CreateBranchDTO(BaseModel):
    """DTO for creating a new branch."""
    novel_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    parent_branch_id: Optional[str] = None
    fork_episode: int = Field(default=0, ge=0)

    model_config = MODEL_CONFIG_DEFAULTS


class UpdateBranchDTO(BaseModel):
    """DTO for updating a branch."""
    name: Optional[str] = Field(None, min_length=1)
    graph_data: Optional[Dict[str, Any]] = None
    # Note: novel_id, parent_branch_id, fork_episode are typically not updated after creation

    model_config = MODEL_CONFIG_DEFAULTS


class BranchResponseDTO(BaseModel):
    """DTO for branch response."""
    id: str
    novel_id: str
    name: str
    parent_branch_id: Optional[str]
    fork_episode: int
    graph_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, branch: "Branch") -> "BranchResponseDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(branch.id),
            novel_id=str(branch.novel_id),
            name=branch.name,
            parent_branch_id=str(branch.parent_branch_id) if branch.parent_branch_id else None,
            fork_episode=branch.fork_episode,
            graph_data=branch.graph_data,
            created_at=branch.created_at,
            updated_at=branch.updated_at,
        )


class BranchListItemDTO(BaseModel):
    """DTO for branch list item (lightweight)."""
    id: str
    novel_id: str
    name: str
    is_main: bool
    created_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, branch: "Branch") -> "BranchListItemDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(branch.id),
            novel_id=str(branch.novel_id),
            name=branch.name,
            is_main=branch.is_main_branch(),
            created_at=branch.created_at,
        )


class CreateBranchPlaySessionDTO(BaseModel):
    """DTO for creating a branch play session."""
    novel_id: str = Field(..., min_length=1)
    branch_id: str = Field(..., min_length=1)
    initial_node_id: Optional[str] = None

    model_config = MODEL_CONFIG_DEFAULTS


class BranchPlaySessionResponseDTO(BaseModel):
    """DTO for branch play session response."""
    id: str
    novel_id: str
    branch_id: str
    current_node_id: Optional[str]
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, session: "BranchPlaySession") -> "BranchPlaySessionResponseDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(session.id),
            novel_id=str(session.novel_id),
            branch_id=str(session.branch_id),
            current_node_id=session.current_node_id,
            status=session.status.value,
            version=session.version,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    pass
