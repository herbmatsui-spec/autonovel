from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.domain.models.prompt_version import PromptVersionDbModel


class PromptService(ABC):
    """Abstract service interface for prompt rendering and version management."""

    @abstractmethod
    async def render(
        self,
        template_name: str,
        context: dict[str, Any],
        book_id: int | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
    ) -> str:
        """Render a prompt template with context."""
        ...

    @abstractmethod
    async def render_async(
        self,
        template_name: str,
        context: dict[str, Any],
        book_id: int | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
    ) -> str:
        """Async render a prompt template with context."""
        ...

    @abstractmethod
    async def get_active_version(
        self, book_id: int, prompt_key: str
    ) -> PromptVersionDbModel | None:
        """Get the currently active prompt version."""
        ...

    @abstractmethod
    async def activate_version(self, book_id: int, prompt_key: str, version_id: int) -> None:
        """Activate a specific prompt version."""
        ...

    @abstractmethod
    async def create_version(
        self,
        book_id: int,
        prompt_key: str,
        version_tag: str,
        content: str,
        score_before: float | None = None,
        ab_test_metrics: dict[str, Any] | None = None,
    ) -> PromptVersionDbModel:
        """Create a new prompt version."""
        ...

    @abstractmethod
    async def list_versions(self, book_id: int, limit: int = 20) -> list[PromptVersionDbModel]:
        """List prompt versions for a book."""
        ...

    @abstractmethod
    async def update_score_after(self, version_id: int, score: float) -> None:
        """Update the post-A/B test score."""
        ...

    @abstractmethod
    async def update_ab_test_metrics(self, version_id: int, metrics: dict[str, Any]) -> None:
        """Update A/B test metrics."""
        ...

    @abstractmethod
    async def record_rollback(self, version_id: int, reason: str) -> None:
        """Record a rollback and deactivate version."""
        ...
