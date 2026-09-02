from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Genre:
    """Genre value object representing the story's genre."""

    name: str

    def __str__(self) -> str:
        return self.name
