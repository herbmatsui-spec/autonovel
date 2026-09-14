"""ID value objects - UUID wrappers for type-safe identifiers."""

from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class NovelId:
    """Novel (Book) identifier."""
    value: UUID

    @classmethod
    def generate(cls) -> NovelId:
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> NovelId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return int(self.value)


@dataclass(frozen=True, slots=True)
class ChapterId:
    """Chapter identifier."""
    value: UUID

    @classmethod
    def generate(cls) -> ChapterId:
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> ChapterId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return int(self.value)


@dataclass(frozen=True, slots=True)
class EpisodeId:
    """Episode identifier (episode number within a novel)."""
    value: int

    @classmethod
    def from_int(cls, value: int) -> EpisodeId:
        if value < 1:
            raise ValueError("Episode number must be positive")
        return cls(value)

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return self.value


@dataclass(frozen=True, slots=True)
class CharacterId:
    """Character identifier."""
    value: UUID

    @classmethod
    def generate(cls) -> CharacterId:
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> CharacterId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return int(self.value)


@dataclass(frozen=True, slots=True)
class BranchId:
    """Branch identifier."""
    value: UUID

    @classmethod
    def generate(cls) -> BranchId:
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> BranchId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return int(self.value)


@dataclass(frozen=True, slots=True)
class PlotId:
    """Plot identifier."""
    value: UUID

    @classmethod
    def generate(cls) -> PlotId:
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> PlotId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return int(self.value)


@dataclass(frozen=True, slots=True)
class SettingId:
    """Setting identifier."""
    value: UUID

    @classmethod
    def generate(cls) -> SettingId:
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> SettingId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return int(self.value)


@dataclass(frozen=True, slots=True)
class LoreId:
    """Lore identifier."""
    value: UUID

    @classmethod
    def generate(cls) -> LoreId:
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> LoreId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return int(self.value)


@dataclass(frozen=True, slots=True)
class PlotPointId:
    """Plot point identifier."""
    value: UUID

    @classmethod
    def generate(cls) -> PlotPointId:
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> PlotPointId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return int(self.value)


@dataclass(frozen=True, slots=True)
class ArcId:
    """Arc identifier."""
    value: UUID

    @classmethod
    def generate(cls) -> ArcId:
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> ArcId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return int(self.value)


@dataclass(frozen=True, slots=True)
class AuditId:
    """Audit identifier."""
    value: UUID

    @classmethod
    def generate(cls) -> AuditId:
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> AuditId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return int(self.value)


@dataclass(frozen=True, slots=True)
class UserId:
    """User identifier."""
    value: UUID

    @classmethod
    def generate(cls) -> UserId:
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> UserId:
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return int(self.value)


__all__ = [
    "NovelId",
    "ChapterId",
    "EpisodeId",
    "CharacterId",
    "BranchId",
    "PlotId",
    "SettingId",
    "LoreId",
    "PlotPointId",
    "ArcId",
    "AuditId",
    "UserId",
]