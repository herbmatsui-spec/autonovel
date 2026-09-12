"""Text content value objects."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class TextFormat(Enum):
    """Text format types."""
    PLAIN = "plain"
    MARKDOWN = "markdown"
    HTML = "html"


@dataclass(frozen=True, slots=True)
class TextContent:
    """Base text content value object."""
    content: str
    format: TextFormat = TextFormat.PLAIN

    def __post_init__(self) -> None:
        if not isinstance(self.content, str):
            raise TypeError("Content must be a string")
        if self.content is None:
            object.__setattr__(self, "content", "")

    def as_plain(self) -> str:
        return self.content

    def as_markdown(self) -> str:
        if self.format == TextFormat.MARKDOWN:
            return self.content
        return self.content

    def word_count(self) -> int:
        return len(self.content.split())

    def char_count(self) -> int:
        return len(self.content)

    def is_empty(self) -> bool:
        return not self.content.strip()

    def __len__(self) -> int:
        return len(self.content)

    def __str__(self) -> str:
        return self.content

    def __add__(self, other: TextContent) -> TextContent:
        if not isinstance(other, TextContent):
            return NotImplemented
        return TextContent(
            content=self.content + other.content,
            format=self.format if self.format == other.format else TextFormat.PLAIN
        )


@dataclass(frozen=True, slots=True)
class PlainText(TextContent):
    """Plain text content."""
    content: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "format", TextFormat.PLAIN)


@dataclass(frozen=True, slots=True)
class MarkdownText(TextContent):
    """Markdown formatted text content."""
    content: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "format", TextFormat.MARKDOWN)


@dataclass(frozen=True, slots=True)
class HtmlText(TextContent):
    """HTML formatted text content."""
    content: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "format", TextFormat.HTML)


@dataclass(frozen=True, slots=True)
class Title:
    """Title value object with validation."""
    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValueError("Title cannot be empty")
        if len(self.value) > 200:
            raise ValueError("Title cannot exceed 200 characters")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Summary:
    """Summary/description value object."""
    value: str

    def __post_init__(self) -> None:
        if self.value is None:
            object.__setattr__(self, "value", "")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Catchcopy:
    """Catchcopy/tagline value object."""
    value: str

    def __post_init__(self) -> None:
        if self.value is None:
            object.__setattr__(self, "value", "")
        if len(self.value) > 255:
            raise ValueError("Catchcopy cannot exceed 255 characters")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Genre:
    """Genre value object."""
    value: str

    def __post_init__(self) -> None:
        if self.value is None:
            object.__setattr__(self, "value", "")

    def __str__(self) -> str:
        return self.value


__all__ = [
    "TextFormat",
    "TextContent",
    "PlainText",
    "MarkdownText",
    "HtmlText",
    "Title",
    "Summary",
    "Catchcopy",
    "Genre",
]