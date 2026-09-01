from __future__ import annotations

from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.domain.interfaces.prompt_repository import PromptVersionRepository
from src.domain.interfaces.prompt_service import PromptService as PromptServiceInterface
from src.domain.models.prompt_version import PromptVersionDbModel
from src.domain.services.ab_test_router import ABTestRouter


class PromptService(PromptServiceInterface):
    """Implementation of prompt service using repository and AB test router."""

    def __init__(
        self,
        repository: PromptVersionRepository,
        ab_test_router: ABTestRouter = None,
        templates_dir: str = None,
        cache_max_size: int = 100,
    ):
        self._repository = repository
        self._router = ab_test_router or ABTestRouter()
        self._cache_max_size = cache_max_size

        # Set up Jinja2 environment for template loading
        if templates_dir:
            self._templates_dir = templates_dir
        else:
            import os

            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self._templates_dir = os.path.join(current_dir, "..", "..", "prompts")

        self._env = Environment(
            loader=FileSystemLoader(self._templates_dir),
            autoescape=select_autoescape(),
        )

        # Cache for rendered templates
        self._source_cache: Dict[str, str] = {}
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}

    async def render(
        self,
        template_name: str,
        context: Dict[str, Any],
        book_id: Optional[int] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> str:
        """Render a prompt template, preferring DB version if available."""
        source = await self._get_source(template_name, book_id, user_id, request_id)
        template = self._env.from_string(source)
        return template.render(**context)

    async def render_async(
        self,
        template_name: str,
        context: Dict[str, Any],
        book_id: Optional[int] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> str:
        """Async render - delegates to render for now (templates are stateless)."""
        return await self.render(template_name, context, book_id, user_id, request_id)

    async def _get_source(
        self,
        template_name: str,
        book_id: Optional[int],
        user_id: Optional[str],
        request_id: Optional[str],
    ) -> str:
        """Get template source, preferring DB version for book_id."""
        # Normalize template name (add .j2 if needed)
        if not template_name.endswith(".j2") and not template_name.endswith(".html"):
            template_name = f"{template_name}.j2"

        # Check DB for active version first
        if book_id:
            active_version = await self.get_active_version(book_id, template_name)
            if active_version and active_version.is_active:
                return active_version.content

        # Fall back to file system
        if template_name in self._source_cache:
            return self._source_cache[template_name]

        try:
            # Try to get from Jinja2 environment
            template = self._env.get_template(template_name)
            source = template.source if hasattr(template, "source") else str(template)
            self._source_cache[template_name] = source
            return source
        except Exception:
            # Template not found on file system
            raise FileNotFoundError(f"Prompt template '{template_name}' not found")

    async def get_active_version(
        self, book_id: int, prompt_key: str
    ) -> Optional[PromptVersionDbModel]:
        """Get the currently active prompt version."""
        return await self._repository.get_active_prompt_version(book_id, prompt_key)

    async def create_version(
        self,
        book_id: int,
        prompt_key: str,
        version_tag: str,
        content: str,
        score_before: Optional[float] = None,
        ab_test_metrics: Optional[Dict[str, Any]] = None,
    ) -> PromptVersionDbModel:
        """Create a new prompt version."""
        return await self._repository.create_prompt_version(
            book_id=book_id,
            prompt_key=prompt_key,
            version_tag=version_tag,
            content=content,
            score_before=score_before,
            ab_test_metrics=ab_test_metrics,
            is_active=False,
        )

    async def activate_version(self, book_id: int, prompt_key: str, version_id: int) -> None:
        """Activate a specific prompt version."""
        await self._repository.set_active_prompt_version(book_id, prompt_key, version_id)

    async def list_versions(self, book_id: int, limit: int = 20) -> List[PromptVersionDbModel]:
        """List prompt versions for a book."""
        return await self._repository.get_prompt_versions(book_id, limit)

    async def update_score_after(self, version_id: int, score: float) -> None:
        """Update the post-A/B test score."""
        await self._repository.update_score_after(version_id, score)

    async def update_ab_test_metrics(self, version_id: int, metrics: Dict[str, Any]) -> None:
        """Update A/B test metrics."""
        await self._repository.update_ab_test_metrics(version_id, metrics)

    async def record_rollback(self, version_id: int, reason: str) -> None:
        """Record a rollback and deactivate version."""
        await self._repository.record_rollback(version_id, reason)


class PromptRegistry:
    """Registry for managing prompt templates with versioning and A/B testing support."""

    def __init__(
        self,
        prompt_service: PromptService = None,
        ab_test_router: ABTestRouter = None,
        templates_dir: str = None,
        cache_max_size: int = 100,
    ):
        self._service = prompt_service
        self._router = ab_test_router or ABTestRouter()
        self._cache_max_size = cache_max_size
        self._cache: Dict[str, Any] = {}

        if templates_dir:
            self._templates_dir = templates_dir
        else:
            import os

            current_dir = os.path.dirname(os.path.abspath(__file__))
            self._templates_dir = os.path.join(current_dir, "..", "prompts")

    def get_template_source(self, template_name: str, book_id: Optional[int] = None) -> str:
        """Get raw template source (for caching purposes)."""
        cache_key = f"{book_id or 'global'}:{template_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        env = Environment(
            loader=FileSystemLoader(self._templates_dir),
            autoescape=select_autoescape(),
        )

        try:
            template = env.get_template(template_name)
            source = template.source if hasattr(template, "source") else str(template)
            self._cache[cache_key] = source
            return source
        except Exception:
            raise FileNotFoundError(f"Template '{template_name}' not found")

    async def render_for_user(
        self,
        template_name: str,
        context: Dict[str, Any],
        user_id: str,
        request_id: Optional[str] = None,
        book_id: Optional[int] = None,
        version_tags: Optional[List[str]] = None,
    ) -> str:
        """Render template with A/B variant selection based on user/request."""
        if self._service and book_id:
            return await self._service.render_async(
                template_name, context, book_id, user_id, request_id
            )

        # AB test variant selection from file system
        source = await self._get_ab_variant(
            template_name, book_id, user_id, request_id, version_tags
        )

        env = Environment(
            loader=FileSystemLoader(self._templates_dir),
            autoescape=select_autoescape(),
        )
        template = env.from_string(source)
        return template.render(**context)

    async def _get_ab_variant(
        self,
        template_name: str,
        book_id: Optional[int],
        user_id: str,
        request_id: Optional[str],
        version_tags: Optional[List[str]],
    ) -> str:
        """Get A/B variant based on user bucketing."""
        # Try DB version first
        if self._service and book_id:
            active = await self._service.get_active_version(book_id, template_name)
            if active:
                return active.content

        # Fall back to file system with tag-based variant selection
        if version_tags:
            selected_tag = self._router.get_version_tag(user_id, version_tags, request_id)
            variant_name = template_name.replace(".j2", f"_{selected_tag}.j2")
            try:
                return self.get_template_source(variant_name, book_id)
            except FileNotFoundError:
                pass

        return self.get_template_source(template_name, book_id)
