"""Scene domain entity for beat-to-scene split writing."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum

from src.domain.value_objects.ids import NovelId, SceneId


class SceneRole(Enum):
    """Role of a scene within an episode (3-scene structure)."""
    INTRODUCTION = "導入"      # Scene 1: Setup, world-building, character introduction
    CONFLICT = "衝突"          # Scene 2: Main conflict, tension escalation
    HOOK = "引き"              # Scene 3: Cliffhanger, hook for next episode


class SceneStatus(Enum):
    """Scene generation status."""
    PLANNED = "planned"
    WRITING = "writing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Scene:
    """Individual scene within an episode (beat-to-scene split)."""
    id: SceneId
    novel_id: NovelId
    branch_id: NovelId
    episode_number: int
    scene_number: int  # 1, 2, or 3
    role: SceneRole
    title: str
    summary: str = ""
    content: str = ""
    target_word_count: int = 800  # ~1/3 of episode target
    actual_word_count: int = 0
    tension_start: int = 0  # Tension at scene start (0-100)
    tension_end: int = 0    # Tension at scene end (0-100)
    status: SceneStatus = SceneStatus.PLANNED
    beats: List[str] = field(default_factory=list)  # Narrative beats to hit
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    generation_metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 1 <= self.scene_number <= 3:
            raise ValueError("Scene number must be 1, 2, or 3")
        if self.target_word_count < 100:
            raise ValueError("Target word count must be at least 100")

    @classmethod
    def create_introduction(
        cls,
        novel_id: NovelId,
        branch_id: NovelId,
        episode_number: int,
        target_word_count: int = 800,
        beats: Optional[List[str]] = None,
    ) -> Scene:
        """Create the introduction scene (導入)."""
        return cls(
            id=SceneId.generate(),
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=episode_number,
            scene_number=1,
            role=SceneRole.INTRODUCTION,
            title="導入",
            target_word_count=target_word_count,
            tension_start=20,
            tension_end=50,
            beats=beats or [
                "日常/現状の提示",
                "主人公の目的/動機の暗示",
                "小さな事件/違和感の導入",
            ],
        )

    @classmethod
    def create_conflict(
        cls,
        novel_id: NovelId,
        branch_id: NovelId,
        episode_number: int,
        target_word_count: int = 800,
        beats: Optional[List[str]] = None,
    ) -> Scene:
        """Create the conflict scene (衝突)."""
        return cls(
            id=SceneId.generate(),
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=episode_number,
            scene_number=2,
            role=SceneRole.CONFLICT,
            title="衝突",
            target_word_count=target_word_count,
            tension_start=50,
            tension_end=85,
            beats=beats or [
                "主要な対立/困難の顕在化",
                "主人公の試行錯誤/葛藤",
                "ピンチ/絶体絶命の状況",
            ],
        )

    @classmethod
    def create_hook(
        cls,
        novel_id: NovelId,
        branch_id: NovelId,
        episode_number: int,
        target_word_count: int = 800,
        beats: Optional[List[str]] = None,
    ) -> Scene:
        """Create the hook/cliffhanger scene (引き)."""
        return cls(
            id=SceneId.generate(),
            novel_id=novel_id,
            branch_id=branch_id,
            episode_number=episode_number,
            scene_number=3,
            role=SceneRole.HOOK,
            title="引き",
            target_word_count=target_word_count,
            tension_start=85,
            tension_end=95,
            beats=beats or [
                "最大の危機/クライマックス",
                "意外な展開/伏線の回収",
                "次回への強烈なフック/クリフハンガー",
            ],
        )

    @classmethod
    def create_standard_triad(
        cls,
        novel_id: NovelId,
        branch_id: NovelId,
        episode_number: int,
        target_word_count: int = 2400,
        custom_beats: Optional[dict[SceneRole, List[str]]] = None,
    ) -> List[Scene]:
        """Create the standard 3-scene structure for an episode."""
        per_scene = target_word_count // 3
        return [
            cls.create_introduction(
                novel_id, branch_id, episode_number,
                target_word_count=per_scene,
                beats=custom_beats.get(SceneRole.INTRODUCTION) if custom_beats else None,
            ),
            cls.create_conflict(
                novel_id, branch_id, episode_number,
                target_word_count=per_scene,
                beats=custom_beats.get(SceneRole.CONFLICT) if custom_beats else None,
            ),
            cls.create_hook(
                novel_id, branch_id, episode_number,
                target_word_count=per_scene,
                beats=custom_beats.get(SceneRole.HOOK) if custom_beats else None,
            ),
        ]

    def mark_writing(self) -> None:
        """Mark scene as being written."""
        self.status = SceneStatus.WRITING
        self.updated_at = datetime.now()

    def mark_completed(self, content: str) -> None:
        """Mark scene as completed with generated content."""
        self.content = content
        self.actual_word_count = len(content)
        self.status = SceneStatus.COMPLETED
        self.updated_at = datetime.now()

    def mark_failed(self, error: str) -> None:
        """Mark scene as failed."""
        self.status = SceneStatus.FAILED
        self.generation_metadata["error"] = error
        self.updated_at = datetime.now()

    def get_tension_delta(self) -> int:
        """Get tension change across this scene."""
        return self.tension_end - self.tension_start

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "novel_id": str(self.novel_id),
            "branch_id": str(self.branch_id),
            "episode_number": self.episode_number,
            "scene_number": self.scene_number,
            "role": self.role.value,
            "title": self.title,
            "summary": self.summary,
            "content": self.content,
            "target_word_count": self.target_word_count,
            "actual_word_count": self.actual_word_count,
            "tension_start": self.tension_start,
            "tension_end": self.tension_end,
            "tension_delta": self.get_tension_delta(),
            "status": self.status.value,
            "beats": self.beats,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "generation_metadata": self.generation_metadata,
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Scene):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


__all__ = [
    "Scene",
    "SceneRole",
    "SceneStatus",
]
