from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CharacterRole:
    """Character role value object representing the character's function in the story."""

    name: str

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        # Dummy implementation for potential numeric role mapping
        return hash(self.name) % 100
