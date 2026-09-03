from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.domain.models.prompt_version import PromptVersionDbModel


class PromptVersionRepository(ABC):
    """Abstract repository interface for prompt version persistence."""

    @abstractmethod
    async def create_prompt_version(
        self,
        book_id: int,
        prompt_key: str,
        version_tag: str,
        content: str,
        score_before: float | None = None,
        score_after: float | None = None,
        ab_test_metrics: dict[str, Any] | None = None,
        is_active: bool = False,
    ) -> PromptVersionDbModel:
        """Create a new prompt version."""
        ...

    @abstractmethod
    async def get_prompt_version(self, version_id: int) -> PromptVersionDbModel | None:
        """Get a prompt version by its ID."""
        ...

    @abstractmethod
    async def get_prompt_version_by_tag(
        self, book_id: int, prompt_key: str, version_tag: str
    ) -> PromptVersionDbModel | None:
        """Get a prompt version by book ID, prompt key, and version tag."""
        ...

    @abstractmethod
    async def get_prompt_versions(
        self, book_id: int, limit: int = 20
    ) -> list[PromptVersionDbModel]:
        """Get prompt versions for a book, ordered by creation date (descending)."""
        ...

    @abstractmethod
    async def get_active_prompt_version(
        self, book_id: int, prompt_key: str
    ) -> PromptVersionDbModel | None:
        """Get the currently active prompt version for a book and prompt key."""
        ...

    @abstractmethod
    async def set_active_prompt_version(
        self, book_id: int, prompt_key: str, version_id: int
    ) -> None:
        """Set a prompt version as active (deactivating others for the same book/prompt key)."""
        ...

    @abstractmethod
    async def update_score_after(self, version_id: int, score: float) -> None:
        """Update the post-A/B test score for a prompt version."""
        ...

    @abstractmethod
    async def update_ab_test_metrics(self, version_id: int, metrics: dict[str, Any]) -> None:
        """Update the A/B test metrics for a prompt version."""
        ...

    @abstractmethod
    async def record_rollback(self, version_id: int, reason: str) -> None:
        """Record a rollback reason and deactivate the prompt version."""
        ...
