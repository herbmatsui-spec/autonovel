"""Character domain entity."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import uuid4

from src.domain.value_objects.ids import NovelId, CharacterId
from src.domain.value_objects.metadata import CharacterMetadata


@dataclass
class Character:
    """Character aggregate root."""
    id: CharacterId
    novel_id: NovelId
    name: str
    role: str
    personality: str = ""
    ability: str = ""
    registry_data: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Relationships (stored as references)
    _arcs: list[CharacterArc] = field(default_factory=list, init=False, repr=False)

    @classmethod
    def create(
        cls,
        novel_id: NovelId,
        name: str,
        role: str,
        personality: str = "",
        ability: str = "",
    ) -> Character:
        """Factory method to create a new character."""
        char_id = CharacterId.generate()
        now = datetime.now()
        return cls(
            id=char_id,
            novel_id=novel_id,
            name=name,
            role=role,
            personality=personality,
            ability=ability,
            registry_data="",
            created_at=now,
            updated_at=now,
        )

    def update_details(
        self,
        name: Optional[str] = None,
        role: Optional[str] = None,
        personality: Optional[str] = None,
        ability: Optional[str] = None,
        registry_data: Optional[str] = None,
    ) -> None:
        """Update character details."""
        if name is not None:
            if not name.strip():
                raise ValueError("Character name cannot be empty")
            self.name = name
        if role is not None:
            self.role = role
        if personality is not None:
            self.personality = personality
        if ability is not None:
            self.ability = ability
        if registry_data is not None:
            self.registry_data = registry_data
        self.updated_at = datetime.now()

    def add_arc(self, arc: CharacterArc) -> None:
        """Add a character arc."""
        if arc.character_id != self.id:
            raise ValueError("Arc character_id must match this character")
        if arc.novel_id != self.novel_id:
            raise ValueError("Arc novel_id must match this character's novel")
        self._arcs.append(arc)

    def get_arcs(self) -> list[CharacterArc]:
        """Get all character arcs."""
        return list(self._arcs)

    def get_current_arc(self) -> Optional[CharacterArc]:
        """Get the current active arc."""
        for arc in self._arcs:
            if not arc.is_completed:
                return arc
        return None

    def to_metadata(self) -> CharacterMetadata:
        """Convert to metadata value object."""
        return CharacterMetadata(
            character_id=NovelId(self.id.value),  # Convert CharacterId to NovelId (both UUID)
            novel_id=self.novel_id,
            name=self.name,
            role=self.role,
            personality=self.personality,
            ability=self.ability,
            registry_data=self.registry_data,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Character):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


@dataclass
class CharacterArc:
    """Character arc entity."""
    id: CharacterId  # Using CharacterId as generic UUID
    novel_id: NovelId
    character_id: CharacterId
    arc_name: str
    arc_stages: list[str] = field(default_factory=list)
    current_stage_index: int = 0
    is_completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.arc_name.strip():
            raise ValueError("Arc name cannot be empty")

    @classmethod
    def create(
        cls,
        novel_id: NovelId,
        character_id: CharacterId,
        arc_name: str,
        stages: list[str],
    ) -> CharacterArc:
        """Factory method to create a new character arc."""
        arc_id = CharacterId.generate()
        now = datetime.now()
        return cls(
            id=arc_id,
            novel_id=novel_id,
            character_id=character_id,
            arc_name=arc_name,
            arc_stages=stages,
            current_stage_index=0,
            is_completed=False,
            created_at=now,
            updated_at=now,
        )

    def advance_stage(self) -> bool:
        """Advance to next stage. Returns True if arc is now complete."""
        if self.current_stage_index < len(self.arc_stages) - 1:
            self.current_stage_index += 1
            self.updated_at = datetime.now()
            return False
        else:
            self.is_completed = True
            self.updated_at = datetime.now()
            return True

    def get_current_stage(self) -> Optional[str]:
        """Get current stage name."""
        if 0 <= self.current_stage_index < len(self.arc_stages):
            return self.arc_stages[self.current_stage_index]
        return None

    def get_progress(self) -> float:
        """Get progress as 0.0-1.0."""
        if not self.arc_stages:
            return 0.0
        return (self.current_stage_index + 1) / len(self.arc_stages)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CharacterArc):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


__all__ = [
    "Character",
    "CharacterArc",
]