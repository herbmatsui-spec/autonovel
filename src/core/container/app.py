"""
AppContainer - アプリケーション層のDIコンテナ
InfraContainer を継承し、エージェント・サービス・エンジンを定義する。
"""

from __future__ import annotations

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


class AppContainer(InfraContainer):
    api_key: providers.Object = providers.Object("DUMMY")

    genai_client: providers.Singleton = providers.Singleton(
        "src.core.llm_gateway.create_genai_client",
        api_key=api_key,
    )
    llm_factory: providers.Singleton = providers.Singleton(
        "src.core.llm_gateway.LLMProviderFactory",
        genai_client=genai_client,
        cooldown=InfraContainer.cooldown,
    )
    semantic_cache: providers.Singleton = providers.Singleton(
        "src.core.llm_gateway.SemanticCacheManager",
        vector_store=InfraContainer.vector_store,
    )
    edge_preserver: providers.Singleton = providers.Singleton(
        "src.backend.sharp_edge_preserver.SemanticEdgePreserver",
        semantic_cache=semantic_cache,
        similarity_threshold=0.75,
        use_semantic=True,
    )
    llm: providers.Singleton = providers.Singleton(
        "src.core.llm_gateway.LLMGenerateResultProxy",
        llm_factory=llm_factory,
    )
    connection_pipeline: providers.Singleton = providers.Singleton(lambda: None)

    repo: providers.Singleton = providers.Singleton(
        DataRepository,
        db=InfraContainer.db,
    )
    uow: providers.Factory = providers.Factory(
        UnitOfWork,
        db=InfraContainer.db,
    )

    plot_service: providers.Factory = providers.Factory(
        "src.services.plot_service.PlotService",
        repo=repo,
    )

    pm: providers.Singleton = providers.Singleton(
        "prompts.manager.PromptManager",
    )

    ctx_mgr: providers.Singleton = providers.Singleton(
        ContextManager,
        repo=repo,
    )

    auditor: providers.Singleton = providers.Singleton(
        "src.agents.audit.LogicalAuditor",
        repo=repo,
        pm=pm,
        llm=llm,
    )
    marketing: providers.Singleton = providers.Singleton(
        "src.agents.MarketingAgent",
        repo=repo,
        prompt_manager=pm,
        llm=llm,
    )
    bible_generator: providers.Singleton = providers.Singleton(
        "src.services.bible_service.WorldBibleGenerator",
        repo=repo,
        llm=llm,
        pm=pm,
        debate=None,
        marketing=marketing,
        auditor=auditor,
    )
    plot_expander: providers.Singleton = providers.Singleton(
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
    planner: providers.Singleton = providers.Singleton(
        "src.agents.PlanningAgent",
        repo=repo,
        llm=llm,
        prompt_manager=pm,
    )
    validator: providers.Singleton = providers.Singleton(
        "src.agents.audit.LogicalAuditor",
        repo=repo,
        pm=pm,
        llm=llm,
    )
    narrative: providers.Singleton = providers.Singleton(
        "src.backend.engine_narrative.NarrativeController",
        repo=repo,
        pm=pm,
        ctx_mgr=ctx_mgr,
        generate_json=llm.provided.generate_json,
        logic_validator=validator,
        auditor=auditor,
    )
    critique: providers.Singleton = providers.Singleton(
        "src.backend.engine_critique.CritiqueAgent",
        repo=repo,
        pm=pm,
        generate_json=llm.provided.generate_json,
    )
    style_rag: providers.Singleton = providers.Singleton(
        "src.backend.engine_style_rag.StyleRagManager",
        client=genai_client,
        repo=repo,
    )
    writer: providers.Singleton = providers.Singleton(
        "src.agents.WritingAgent",
        repo=repo,
        llm=llm,
        style_rag=style_rag,
        plot_expander=plot_expander,
    )
    formatter: providers.Singleton = providers.Singleton(
        "src.backend.sanitizer.TextFormatter",
    )
    engine: providers.Factory = providers.Factory(
        "src.backend.engine.UltimateHegemonyEngine",
        api_key=api_key,
        repo=repo,
        db=InfraContainer.db,
        llm=llm,
        cooldown=InfraContainer.cooldown,
        plot_service=plot_service,
    )
    engine_facade: providers.Factory = providers.Factory(
        "src.backend.engine_facade.EngineFacade",
        config=providers.Factory(
            EngineConfig.create,
            api_key=api_key,
            cooldown=InfraContainer.cooldown,
        ),
        engine=engine,
    )
    redis_cache: providers.Factory = providers.Factory(
        "src.services.redis_cache.RedisCacheService"
    )
    prompt_cache: providers.Factory = providers.Factory(
        "src.services.redis_cache.PromptCacheService",
        redis_cache=redis_cache,
        semantic_cache=None,
        l1_cache=None,
    )

    image_service: providers.Factory = providers.Factory(
        "src.services.image_service.ImageService",
        api_key=api_key,
    )
    illustration_agent: providers.Factory = providers.Factory(
        "src.agents.illustration_agent.IllustrationAgent",
        image_service=image_service,
    )
    illustration_workflow: providers.Factory = providers.Factory(
        "src.backend.workflows.illustration_workflow.IllustrationWorkflow",
        illustration_agent=illustration_agent,
    )

    # DAG パイプラインのプロバイダー
    dag_pipeline: providers.Singleton = providers.Singleton(
        lambda: (
            # Builder を作成し、SPI ファクトリーを渡す
            __import__('src.backend.workflows.dag_builder', fromlist=['DefaultAutoWorkflowBuilder']).DefaultAutoWorkflowBuilder(
                llm_factory=InfraContainer.llm_provider_factory,
                vector_store_factory=InfraContainer.vector_store_provider_factory,
                image_provider_factory=InfraContainer.image_provider_factory,
            ).build()
        )
    )


# 後方互換エイリアス
AppContainer2 = AppContainer