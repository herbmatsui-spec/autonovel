"""Backward-compatible facade for the legacy engine."""

from __future__ import annotations

import warnings
from typing import Any

from src.agents.orchestrator import Orchestrator
from src.llm.circuit_breaker import LLMCircuitBreaker
from src.llm.resilient_gateway import ResilientLLMGateway


class UltimateHegemonyEngine(Orchestrator):
    def __init__(
        self,
        api_key: str | None = None,
        *args: Any,
        repo: Any | None = None,
        db: Any | None = None,
        llm: Any | None = None,
        cooldown: Any | None = None,
        plot_service: Any | None = None,
        foreshadowing_repository: Any | None = None,
        hook_repository: Any | None = None,
        llm_gateway: ResilientLLMGateway | None = None,
        nodes: Any | None = None,
        event_bus: Any | None = None,
        correlation_id: str | None = None,
        max_backtracks_per_node: int = 3,
        dag_scheduler: Any | None = None,
        use_dag_scheduler: bool = False,
        **legacy: Any,
    ) -> None:
        warnings.warn(
            "UltimateHegemonyEngine is deprecated. Use Orchestrator directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        if args:
            if nodes is None:
                nodes = args[0]
            if len(args) > 1:
                raise TypeError("UltimateHegemonyEngine accepts at most one positional nodes argument")

        self.api_key = api_key
        self.repo = repo
        self.db = db
        self.llm = llm
        self.cooldown = cooldown
        self.foreshadowing_repository = foreshadowing_repository
        self.hook_repository = hook_repository
        self._legacy = legacy
        self.client = legacy.get("client")
        self.current_ep_num = legacy.get("current_ep_num", 0)

        if plot_service is not None:
            self.plot_service = plot_service
        elif repo is not None:
            from src.services.plot_service import PlotService

            self.plot_service = PlotService(repo=repo)
        else:
            self.plot_service = None

        if llm_gateway is None and isinstance(llm, ResilientLLMGateway):
            llm_gateway = llm
        if llm_gateway is None:
            providers = {"openai": llm} if llm is not None else {}
            llm_gateway = ResilientLLMGateway(
                circuit_breaker=LLMCircuitBreaker(),
                providers=providers,
                default_provider="openai",
            )
        self.llm_gateway = llm_gateway

        super().__init__(
            nodes or {},
            event_bus=event_bus,
            correlation_id=correlation_id,
            max_backtracks_per_node=max_backtracks_per_node,
            dag_scheduler=dag_scheduler,
            use_dag_scheduler=use_dag_scheduler,
        )

    def _legacy_dep(self, name: str) -> Any:
        if name not in self._legacy:
            raise AttributeError(
                f"'{self.__class__.__name__}' has no lazy dependency '{name}'. "
                "Inject it via constructor or upgrade the caller."
            )
        return self._legacy[name]

    @property
    def planner(self) -> Any:
        return self._legacy_dep("planner")

    @property
    def planning_agent(self) -> Any:
        return self._legacy_dep("planner")

    @property
    def writer(self) -> Any:
        return self._legacy_dep("writer")

    @property
    def pm(self) -> Any:
        return self._legacy_dep("pm")

    @property
    def ctx_mgr(self) -> Any:
        return self._legacy_dep("ctx_mgr")

    @property
    def formatter(self) -> Any:
        return self._legacy_dep("formatter")

    @property
    def validator(self) -> Any:
        return self._legacy_dep("validator")

    @property
    def auditor(self) -> Any:
        return self._legacy_dep("auditor")

    @property
    def narrative(self) -> Any:
        return self._legacy_dep("narrative")

    @property
    def critique(self) -> Any:
        return self._legacy_dep("critique")

    @property
    def marketing(self) -> Any:
        return self._legacy_dep("marketing")

    @property
    def bible_agent(self) -> Any:
        return self._legacy_dep("bible_agent")

    @property
    def plot_agent(self) -> Any:
        return self._legacy_dep("plot_agent")

    @property
    def style_rag(self) -> Any:
        return self._legacy_dep("style_rag")

    @property
    def illustration_agent(self) -> Any:
        return self._legacy_dep("illustration_agent")

    @property
    def ai_api(self) -> Any:
        warnings.warn(
            "ai_api is deprecated, use llm instead",
            FutureWarning,
            stacklevel=2,
        )
        return self.llm

    @property
    def llm_client(self) -> Any:
        warnings.warn(
            "llm_client is deprecated, use llm instead",
            FutureWarning,
            stacklevel=2,
        )
        return self.llm

    @property
    def logic_validator(self) -> Any:
        return self.validator

    @property
    def generate_json(self) -> Any:
        if self.llm is not None:
            return self.llm.generate_json
        return self.llm_gateway.generate_json

    def dispose(self) -> None:
        if hasattr(self.db, "engine"):
            self.db.engine.dispose()

    async def sync_bible(self, book_id: int, reporter: Any | None = None) -> Any:
        return await self.bible_agent.sync_bible_lifecycle(book_id, reporter=reporter)

    async def resolve_bible_setting(self, setting_id: int, status: str) -> None:
        await self.repo.resolve_pending_setting(setting_id, status)

    async def determine_target_tension(
        self,
        book_id: int,
        ep_num: int,
        genre: str,
        story_type: str | None = None,
    ) -> Any:
        return await self.plot_service.determine_target_tension(
            book_id=book_id,
            ep_num=ep_num,
            genre=genre,
            story_type=story_type,
        )

    async def validate_tension_deviation(
        self,
        ep_num: int,
        generated_tension: float,
        book_id: int,
        tolerance: float = 0.2,
    ) -> Any:
        return await self.plot_service.validate_tension_deviation(
            ep_num=ep_num,
            generated_tension=generated_tension,
            book_id=book_id,
            tolerance=tolerance,
        )

    async def reverse_plot_generation_workflow(
        self,
        answers: dict[str, Any],
        target_episodes: int,
        genre: str,
        reporter: Any | None = None,
    ) -> Any:
        from src.backend.workflows.reverse_plot_workflow import ReversePlotGenerationWorkflow

        workflow = ReversePlotGenerationWorkflow(self.repo, self.pm, self.generate_json)
        return await workflow.execute(
            reporter,
            answers=answers,
            target_episodes=target_episodes,
            genre=genre,
        )


class HookGenerationStep:
    async def execute(self, ctx: Any, engine: Any, reporter: Any) -> bool:
        return True
