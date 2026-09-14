"""Metadata value objects."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

from src.domain.value_objects.ids import NovelId, UserId
from src.domain.value_objects.text import Title, Genre, Catchcopy, Summary
from src.domain.value_objects.scores import BookScore, QolScore, CostScore


class NovelStatus(Enum):
    """Novel status enumeration."""
    DRAFT = "draft"
    WRITING = "writing"
    EDITING = "editing"
    COMPLETED = "completed"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class NovelMode(Enum):
    """Novel writing mode."""
    EASY = "easy"
    NORMAL = "normal"
    EXPERT = "expert"


class SettingType(Enum):
    """Setting type enumeration for World Bible."""
    WORLDVIEW = "worldview"
    CHARACTER = "character"
    TERMINOLOGY = "terminology"
    LOCATION = "location"
    ORGANIZATION = "organization"
    ITEM = "item"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class NovelMetadata:
    """Novel metadata value object."""
    novel_id: NovelId
    title: Title
    author_id: UserId
    genre: Genre
    catchcopy: Catchcopy
    synopsis: Summary
    concept: Summary
    status: NovelStatus = NovelStatus.DRAFT
    mode: NovelMode = NovelMode.EASY
    target_episodes: int = 50
    style_dna: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Computed/aggregated metrics
    cumulative_tension: int = 0
    cumulative_qol: int = 0
    cumulative_cost: CostScore = field(default_factory=lambda: CostScore(value=0.0))
    sanctuary_integrity: int = 100
    current_branch_id: Optional[NovelId] = None

    def __post_init__(self) -> None:
        if self.target_episodes < 1:
            raise ValueError("Target episodes must be at least 1")

    def with_updated_timestamp(self) -> NovelMetadata:
        """Return a new instance with updated timestamp."""
        return NovelMetadata(
            novel_id=self.novel_id,
            title=self.title,
            author_id=self.author_id,
            genre=self.genre,
            catchcopy=self.catchcopy,
            synopsis=self.synopsis,
            concept=self.concept,
            status=self.status,
            mode=self.mode,
            target_episodes=self.target_episodes,
            style_dna=self.style_dna,
            created_at=self.created_at,
            updated_at=datetime.now(),
            cumulative_tension=self.cumulative_tension,
            cumulative_qol=self.cumulative_qol,
            cumulative_cost=self.cumulative_cost,
            sanctuary_integrity=self.sanctuary_integrity,
            current_branch_id=self.current_branch_id,
        )


class PublishPlatform(Enum):
    """Publishing platform enumeration."""
    NAROU = "narou"
    KAKUYOMU = "kakuyomu"
    KINDLE = "kindle"
    KOBO = "kobo"
    CUSTOM = "custom"


class PublishStatus(Enum):
    """Publishing status."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class PublishMetadata:
    """Publishing metadata value object."""
    novel_id: NovelId
    platform: PublishPlatform
    episode_range_start: int = 1
    episode_range_end: int = 1
    scheduled_at: Optional[datetime] = None
    status: PublishStatus = PublishStatus.PENDING
    post_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.episode_range_start < 1:
            raise ValueError("Episode range start must be at least 1")
        if self.episode_range_end < self.episode_range_start:
            raise ValueError("Episode range end must be >= start")


@dataclass(frozen=True, slots=True)
class ChapterMetadata:
    """Chapter metadata value object."""
    chapter_id: NovelId  # Using NovelId as generic ID
    novel_id: NovelId
    episode_number: int
    title: Title
    word_count: int = 0
    tension_delta: int = 0
    qol_delta: int = 0
    is_anchor: bool = False
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.episode_number < 1:
            raise ValueError("Episode number must be positive")


@dataclass(frozen=True, slots=True)
class CharacterMetadata:
    """Character metadata value object."""
    character_id: NovelId  # Using NovelId as generic ID
    novel_id: NovelId
    name: str
    role: str
    personality: str = ""
    ability: str = ""
    registry_data: str = ""

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Character name cannot be empty")


@dataclass(frozen=True, slots=True)
class BranchMetadata:
    """Branch metadata value object."""
    branch_id: NovelId
    novel_id: NovelId
    name: str
    parent_branch_id: Optional[NovelId] = None
    fork_episode: int = 0
    graph_data: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Branch name cannot be empty")


@dataclass(frozen=True, slots=True)
class AuditMetadata:
    """Audit metadata value object."""
    audit_id: NovelId
    novel_id: NovelId
    episode_number: int
    category: str
    severity: str
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.episode_number < 1:
            raise ValueError("Episode number must be positive")


__all__ = [
    "NovelStatus",
    "NovelMode",
    "SettingType",
    "NovelMetadata",
    "PublishPlatform",
    "PublishStatus",
    "PublishMetadata",
    "ChapterMetadata",
    "CharacterMetadata",
    "BranchMetadata",
    "AuditMetadata",
]