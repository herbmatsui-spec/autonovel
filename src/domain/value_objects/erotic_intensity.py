from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EroticIntensity:
    """Erotic intensity value object representing erotic content level (0-100)."""

    value: int

    def __post_init__(self):
        if not 0 <= self.value <= 100:
            raise ValueError(f"Erotic intensity must be between 0 and 100, got {self.value}")

    def __str__(self) -> str:
        return str(self.value)

    def __int__(self) -> int:
        return self.value
