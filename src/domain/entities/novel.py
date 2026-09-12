"""Novel domain entity."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from src.domain.value_objects.ids import NovelId, UserId
from src.domain.value_objects.text import Title, Genre, Catchcopy, Summary
from src.domain.value_objects.metadata import NovelStatus, NovelMode, NovelMetadata
from src.domain.value_objects.scores import BookScore, CostScore


@dataclass
class Novel:
    """Novel (Book) aggregate root."""
    id: NovelId
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

    # Aggregated metrics
    cumulative_tension: int = 0
    cumulative_qol: int = 0
    cumulative_cost: CostScore = field(default_factory=lambda: CostScore(value=0.0))
    sanctuary_integrity: int = 100
    current_branch_id: Optional[NovelId] = None

    # Domain events (for event sourcing)
    _events: List[object] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def create(
        cls,
        title: str,
        author_id: UserId,
        genre: str = "",
        catchcopy: str = "",
        synopsis: str = "",
        concept: str = "",
        target_episodes: int = 50,
        mode: NovelMode = NovelMode.EASY,
    ) -> Novel:
        """Factory method to create a new novel."""
        novel_id = NovelId.generate()
        now = datetime.now()
        return cls(
            id=novel_id,
            title=Title(title),
            author_id=author_id,
            genre=Genre(genre),
            catchcopy=Catchcopy(catchcopy),
            synopsis=Summary(synopsis),
            concept=Summary(concept),
            status=NovelStatus.DRAFT,
            mode=mode,
            target_episodes=target_episodes,
            style_dna="",
            created_at=now,
            updated_at=now,
            cumulative_tension=0,
            cumulative_qol=0,
            cumulative_cost=CostScore(value=0.0),
            sanctuary_integrity=100,
            current_branch_id=None,
        )

    def update_metadata(
        self,
        title: Optional[str] = None,
        genre: Optional[str] = None,
        catchcopy: Optional[str] = None,
        synopsis: Optional[str] = None,
        concept: Optional[str] = None,
        target_episodes: Optional[int] = None,
        style_dna: Optional[str] = None,
    ) -> None:
        """Update novel metadata."""
        if title is not None:
            self.title = Title(title)
        if genre is not None:
            self.genre = Genre(genre)
        if catchcopy is not None:
            self.catchcopy = Catchcopy(catchcopy)
        if synopsis is not None:
            self.synopsis = Summary(synopsis)
        if concept is not None:
            self.concept = Summary(concept)
        if target_episodes is not None:
            if target_episodes < 1:
                raise ValueError("Target episodes must be at least 1")
            self.target_episodes = target_episodes
        if style_dna is not None:
            self.style_dna = style_dna
        self.updated_at = datetime.now()

    def change_status(self, status: NovelStatus) -> None:
        """Change novel status."""
        self.status = status
        self.updated_at = datetime.now()

    def set_mode(self, mode: NovelMode) -> None:
        """Set writing mode."""
        self.mode = mode
        self.updated_at = datetime.now()

    def set_current_branch(self, branch_id: NovelId) -> None:
        """Set current active branch."""
        self.current_branch_id = branch_id
        self.updated_at = datetime.now()

    def add_tension(self, delta: int) -> None:
        """Add to cumulative tension."""
        self.cumulative_tension += delta
        self.updated_at = datetime.now()

    def add_qol(self, delta: int) -> None:
        """Add to cumulative QoL."""
        self.cumulative_qol += delta
        self.updated_at = datetime.now()

    def add_cost(self, cost_usd: float, tokens: int = 0) -> None:
        """Add to cumulative cost."""
        self.cumulative_cost = CostScore(
            value=self.cumulative_cost.value + cost_usd,
            tokens_used=self.cumulative_cost.tokens_used + tokens
        )
        self.updated_at = datetime.now()

    def update_sanctuary_integrity(self, value: int) -> None:
        """Update sanctuary integrity (0-100)."""
        if not 0 <= value <= 100:
            raise ValueError("Sanctuary integrity must be between 0 and 100")
        self.sanctuary_integrity = value
        self.updated_at = datetime.now()

    def to_metadata(self) -> NovelMetadata:
        """Convert to metadata value object."""
        return NovelMetadata(
            novel_id=self.id,
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
            updated_at=self.updated_at,
            cumulative_tension=self.cumulative_tension,
            cumulative_qol=self.cumulative_qol,
            cumulative_cost=self.cumulative_cost,
            sanctuary_integrity=self.sanctuary_integrity,
            current_branch_id=self.current_branch_id,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Novel):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass(frozen=True, slots=True)
class Chapter:
    """Chapter entity (belongs to a novel)."""
    id: NovelId  # Using NovelId as generic UUID
    novel_id: NovelId
    branch_id: NovelId
    episode_number: int
    title: Title
    content: str = ""
    score_story: Optional[int] = None
    killer_phrase: str = ""
    summary: str = ""
    world_state: str = ""
    trinity_review_log: str = ""
    ai_insight: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    tension_delta: int = 0
    qol_delta: int = 0
    is_anchor: bool = False

    def __post_init__(self) -> None:
        if self.episode_number < 1:
            raise ValueError("Episode number must be positive")

    @classmethod
    def create(
        cls,
        novel_id: NovelId,
        branch_id: NovelId,
        episode_number: int,
        title: str,
    ) -> Chapter:
        """Factory method to create a new chapter."""
        return cls(
            id=NovelId.generate(),  # Using NovelId as generic UUID
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=episode_number,
            title=Title(title),
            content="",
            created_at=datetime.now(),
        )

    def update_content(self, content: str) -> Chapter:
        """Return new chapter with updated content (immutable)."""
        return Chapter(
            id=self.id,
            novel_id=self.novel_id,
            branch_id=self.branch_id,
            episode_number=self.episode_number,
            title=self.title,
            content=content,
            score_story=self.score_story,
            killer_phrase=self.killer_phrase,
            summary=self.summary,
            world_state=self.world_state,
            trinity_review_log=self.trinity_review_log,
            ai_insight=self.ai_insight,
            created_at=self.created_at,
            tension_delta=self.tension_delta,
            qol_delta=self.qol_delta,
            is_anchor=self.is_anchor,
        )

    def set_score(self, score: int) -> Chapter:
        """Return new chapter with story score."""
        return Chapter(
            id=self.id,
            novel_id=self.novel_id,
            branch_id=self.branch_id,
            episode_number=self.episode_number,
            title=self.title,
            content=self.content,
            score_story=score,
            killer_phrase=self.killer_phrase,
            summary=self.summary,
            world_state=self.world_state,
            trinity_review_log=self.trinity_review_log,
            ai_insight=self.ai_insight,
            created_at=self.created_at,
            tension_delta=self.tension_delta,
            qol_delta=self.qol_delta,
            is_anchor=self.is_anchor,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Chapter):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass(frozen=True, slots=True)
class Episode:
    """Episode entity (alias for chapter in this context)."""
    id: NovelId
    novel_id: NovelId
    branch_id: NovelId
    number: int
    title: Title
    content: str = ""
    plot_summary: str = ""
    tension: int = 50
    catharsis: int = 0
    status: str = "planned"
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError("Episode number must be positive")

    @classmethod
    def create(
        cls,
        novel_id: NovelId,
        branch_id: NovelId,
        number: int,
        title: str,
    ) -> Episode:
        return cls(
            id=NovelId.generate(),
            novel_id=novel_id,
            branch_id=branch_id,
            number=number,
            title=Title(title),
        )


@dataclass(frozen=True, slots=True)
class Volume:
    """Volume entity (collection of chapters/episodes)."""
    id: NovelId
    novel_id: NovelId
    number: int
    title: Title
    start_episode: int
    end_episode: int
    summary: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError("Volume number must be positive")
        if self.start_episode < 1:
            raise ValueError("Start episode must be positive")
        if self.end_episode < self.start_episode:
            raise ValueError("End episode must be >= start episode")


__all__ = [
    "Novel",
    "Chapter",
    "Episode",
    "Volume",
]