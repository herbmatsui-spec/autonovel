"""
AppContainer2 - アプリケーション層のDIコンテナ (後方互換名: AppContainer)
InfraContainer を継承し、エージェント・サービス・エンジンを定義する。
"""
import logging

from dependency_injector import containers, providers

from src.backend.database import DataRepository, UnitOfWork
from src.backend.engine_config import EngineConfig
from src.backend.engine_context import ContextManager
from src.core.container.infra import InfraContainer

logger = logging.getLogger(__name__)


class AppContainer2(InfraContainer):
    wiring_config = containers.WiringConfiguration(
        packages=["src"]
    )

    api_key = providers.Object("DUMMY")

    genai_client = providers.Singleton(
        "src.core.llm_gateway.create_genai_client",
        api_key=api_key,
    )
    llm_factory = providers.Singleton(
        "src.core.llm_gateway.LLMProviderFactory",
        genai_client=genai_client,
        cooldown=InfraContainer.cooldown,
    )
    semantic_cache = providers.Singleton(
        "src.core.llm_gateway.SemanticCacheManager",
        vector_store=InfraContainer.vector_store,
    )
    edge_preserver = providers.Singleton(
        "src.backend.sharp_edge_preserver.SemanticEdgePreserver",
        semantic_cache=semantic_cache,
        similarity_threshold=0.75,
        use_semantic=True,
    )
    llm = providers.Singleton(
        "src.core.llm_gateway.LLMGenerateResultProxy",
        llm_factory=llm_factory,
    )
    connection_pipeline = providers.Singleton(
        lambda: None
    )

    repo = providers.Singleton(
        DataRepository,
        db=InfraContainer.db,
    )
    uow = providers.Factory(
        UnitOfWork,
        db=InfraContainer.db,
    )

    pm = providers.Singleton(
        "prompts.manager.PromptManager",
    )

    ctx_mgr = providers.Singleton(
        ContextManager,
        repo=repo,
    )

    auditor = providers.Singleton(
        "src.agents.LogicalAuditor",
        repo=repo,
        pm=pm,
        llm=llm,
        ctx_mgr=ctx_mgr,
    )
    marketing = providers.Singleton(
        "src.agents.MarketingAgent",
        repo=repo,
        prompt_manager=pm,
        llm=llm,
    )
    bible_generator = providers.Singleton(
        "src.services.bible_service.WorldBibleGenerator",
        repo=repo,
        llm=llm,
        pm=pm,
        debate=None,
        marketing=marketing,
        auditor=auditor,
    )
    plot_expander = providers.Singleton(
        "src.agents.plot.PlotAgent",
        repo=repo,
        pm=pm,
        generate_json=llm.provided.generate_json,
        plot_expander=providers.Singleton(
            "src.services.default_plot_expander.DefaultPlotExpander",
            repo=repo,
            pm=pm,
            llm=llm,
        ),
    )
    planner = providers.Singleton(
        "src.agents.PlanningAgent",
        repo=repo,
        llm=llm,
        prompt_manager=pm,
    )
    validator = providers.Singleton(
        "src.agents.LogicalAuditor",
        repo=repo,
        pm=pm,
        llm=llm,
        ctx_mgr=ctx_mgr,
    )
    narrative = providers.Singleton(
        "src.backend.engine_narrative.NarrativeController",
        repo=repo,
        pm=pm,
        ctx_mgr=ctx_mgr,
        generate_json=llm.provided.generate_json,
        logic_validator=validator,
        auditor=auditor,
    )
    critique = providers.Singleton(
        "src.backend.engine_critique.CritiqueAgent",
        repo=repo,
        pm=pm,
        generate_json=llm.provided.generate_json,
    )
    style_rag = providers.Singleton(
        "src.backend.engine_style_rag.StyleRagManager",
        client=genai_client,
        repo=repo,
    )
    writer = providers.Singleton(
        "src.agents.WritingAgent",
        repo=repo,
        llm=llm,
        prompt_manager=pm,
        style_rag=style_rag,
        plot_expander=plot_expander,
    )
    formatter = providers.Singleton(
        "src.backend.sanitizer.TextFormatter",
    )
    engine = providers.Factory(
        "src.backend.engine.UltimateHegemonyEngine",
        api_key=api_key,
        planner=planner,
        writer=writer,
        repo=repo,
        db=InfraContainer.db,
        pm=pm,
        ctx_mgr=ctx_mgr,
        formatter=formatter,
        validator=validator,
        auditor=auditor,
        narrative=narrative,
        critique=critique,
        marketing=marketing,
        bible_agent=bible_generator,
        plot_agent=plot_expander,
        style_rag=style_rag,
        llm=llm,
        cooldown=InfraContainer.cooldown,
    )
    engine_facade = providers.Factory(
        "src.backend.engine_facade.EngineFacade",
        config=providers.Factory(
            EngineConfig.create,
            api_key=api_key,
            cooldown=InfraContainer.cooldown,
        ),
        engine=engine,
    )
