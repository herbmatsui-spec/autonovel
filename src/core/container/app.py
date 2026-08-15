"""
AppContainer2 - アプリケーション層のDIコンテナ (後方互換名: AppContainer)
InfraContainer を継承し、エージェント・サービス・エンジンを定義する。
"""

import logging
from typing import TYPE_CHECKING

from dependency_injector import providers

from src.backend.database import DataRepository, UnitOfWork
from src.backend.engine_config import EngineConfig
from src.backend.engine_context import ContextManager
from src.core.container.infra import InfraContainer

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AppContainer2(InfraContainer):
    # wiring_config は手動で wire() を呼ぶ運用に変更 (proxy.py 参照)
    # wiring_config = containers.WiringConfiguration(
    #     packages=["src"]
    # )

    api_key = providers.Object("DUMMY")

    genai_client = providers.Singleton["genai.Client"](
        "src.core.llm_gateway.create_genai_client",
        api_key=api_key,
    )
    llm_factory = providers.Singleton["LLMProviderFactory"](
        "src.core.llm_gateway.LLMProviderFactory",
        genai_client=genai_client,
        cooldown=InfraContainer.cooldown,
    )
    semantic_cache = providers.Singleton["SemanticCacheManager"](
        "src.core.llm_gateway.SemanticCacheManager",
        vector_store=InfraContainer.vector_store,
    )
    edge_preserver = providers.Singleton["SemanticEdgePreserver"](
        "src.backend.sharp_edge_preserver.SemanticEdgePreserver",
        semantic_cache=semantic_cache,
        similarity_threshold=0.75,
        use_semantic=True,
    )
    llm = providers.Singleton["LLMGenerateResultProxy"](
        "src.core.llm_gateway.LLMGenerateResultProxy",
        llm_factory=llm_factory,
    )
    connection_pipeline = providers.Singleton(lambda: None)

    repo = providers.Singleton(
        DataRepository,
        db=InfraContainer.db,
    )
    uow = providers.Factory(
        UnitOfWork,
        db=InfraContainer.db,
    )

    plot_service = providers.Factory["PlotService"](
        "src.services.plot_service.PlotService",
        repo=repo,
    )

    pm = providers.Singleton["PromptManager"](
        "prompts.manager.PromptManager",
    )

    ctx_mgr = providers.Singleton(
        ContextManager,
        repo=repo,
    )

    auditor = providers.Singleton["LogicalAuditor"](
        "src.agents.audit.LogicalAuditor",
        repo=repo,
        pm=pm,
        llm=llm,
        ctx_mgr=ctx_mgr,
    )
    marketing = providers.Singleton["MarketingAgent"](
        "src.agents.MarketingAgent",
        repo=repo,
        prompt_manager=pm,
        llm=llm,
    )
    bible_generator = providers.Singleton["WorldBibleGenerator"](
        "src.services.bible_service.WorldBibleGenerator",
        repo=repo,
        llm=llm,
        pm=pm,
        debate=None,
        marketing=marketing,
        auditor=auditor,
    )
    plot_expander = providers.Singleton["PlotAgent"](
        "src.agents.plot.PlotAgent",
        repo=repo,
        pm=pm,
        generate_json=llm.provided.generate_json,
        plot_expander=providers.Singleton["DefaultPlotExpander"](
            "src.services.default_plot_expander.DefaultPlotExpander",
            repo=repo,
            pm=pm,
            llm=llm,
        ),
    )
    planner = providers.Singleton["PlanningAgent"](
        "src.agents.PlanningAgent",
        repo=repo,
        llm=llm,
        prompt_manager=pm,
    )
    validator = providers.Singleton["LogicalAuditor"](
        "src.agents.audit.LogicalAuditor",
        repo=repo,
        pm=pm,
        llm=llm,
        ctx_mgr=ctx_mgr,
    )
    narrative = providers.Singleton["NarrativeController"](
        "src.backend.engine_narrative.NarrativeController",
        repo=repo,
        pm=pm,
        ctx_mgr=ctx_mgr,
        generate_json=llm.provided.generate_json,
        logic_validator=validator,
        auditor=auditor,
    )
    critique = providers.Singleton["CritiqueAgent"](
        "src.backend.engine_critique.CritiqueAgent",
        repo=repo,
        pm=pm,
        generate_json=llm.provided.generate_json,
    )
    style_rag = providers.Singleton["StyleRagManager"](
        "src.backend.engine_style_rag.StyleRagManager",
        client=genai_client,
        repo=repo,
    )
    writer = providers.Singleton["WritingAgent"](
        "src.agents.WritingAgent",
        repo=repo,
        llm=llm,
        prompt_manager=pm,
        style_rag=style_rag,
        plot_expander=plot_expander,
    )
    formatter = providers.Singleton["TextFormatter"](
        "src.backend.sanitizer.TextFormatter",
    )
    engine = providers.Factory["UltimateHegemonyEngine"](
        "src.backend.engine.UltimateHegemonyEngine",
        api_key=api_key,
        repo=repo,
        db=InfraContainer.db,
        llm=llm,
        cooldown=InfraContainer.cooldown,
        plot_service=plot_service,
    )
    engine_facade = providers.Factory["EngineFacade"](
        "src.backend.engine_facade.EngineFacade",
        config=providers.Factory(
            EngineConfig.create,
            api_key=api_key,
            cooldown=InfraContainer.cooldown,
        ),
        engine=engine,
    )
    redis_cache = providers.Factory["RedisCacheService"]("src.services.redis_cache.RedisCacheService")
    prompt_cache = providers.Factory["PromptCacheService"](
        "src.services.redis_cache.PromptCacheService",
        redis_cache=redis_cache,
        semantic_cache=None,
        l1_cache=None,
    )

    image_service = providers.Factory["ImageService"](
        "src.services.image_service.ImageService",
        api_key=api_key,
    )
    illustration_agent = providers.Factory["IllustrationAgent"](
        "src.agents.illustration_agent.IllustrationAgent",
        image_service=image_service,
    )
    illustration_workflow = providers.Factory["IllustrationWorkflow"](
        "src.backend.workflows.illustration_workflow.IllustrationWorkflow",
        illustration_agent=illustration_agent,
    )
