"""
src/core/container.py - 依存性注入コンテナ (AppContainer)
全サービスのDI構成を定義する。
"""

import logging
from dependency_injector import containers, providers

from config import get_config
from prompts.manager import PromptManager
from src.backend.database import DataRepository, UnitOfWork
from src.backend.database.core import get_db_manager
from src.backend.engine_config import EngineConfig
from src.backend.engine_context import ContextManager
from src.core.llm_gateway import (
    LLMGenerateResultProxy,  # noqa: F401  (テスト互�換のため再エクスポート)
)

logger = logging.getLogger(__name__)


class AppContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["src"])

    # 外部入力 (起動時に上書き可能)
    api_key = providers.Object("DUMMY")

    # インフラ
    db = providers.Singleton(get_db_manager)
    vector_store = providers.Singleton(lambda: None)  # ChromaVectorStore �� 必要に応じて差し替え
    audit_logger = providers.Singleton(lambda: None)
    cooldown = providers.Singleton(
        "src.backend.engine_utils.AdaptiveCooldown", base_sec=2.0, min_sec=0.5, max_sec=10.0
    )
    # StatusReporter ファクトリ (PlanningService 等が利用)
    # 注意: src/shared.utils.StatusReporter は Protocol。具象クラスである
    #       src/backend/background.StatusReporter を生成する。
    reporter_factory = providers.Factory("src.backend.background.StatusReporter")
    genai_client = providers.Singleton("src.core.llm_gateway.create_genai_client", api_key=api_key)
    llm_factory = providers.Singleton(
        "src.core.llm_gateway.LLMProviderFactory", genai_client=genai_client, cooldown=cooldown
    )
    semantic_cache = providers.Singleton(
        "src.core.llm_gateway.SemanticCacheManager", vector_store=vector_store
    )
    edge_preserver = providers.Singleton(
        "src.backend.sharp_edge_preserver.SemanticEdgePreserver",
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
    planner = providers.Singleton("src.agents.planning.PlanningAgent", repo=repo, llm=llm, prompt_manager=pm)
    validator = providers.Singleton(
        "src.agents.audit.LogicalAuditor", repo=repo, pm=pm, llm=llm, ctx_mgr=ctx_mgr
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
        pm=pm,
        generate_json=llm.provided.generate_json,
    )
    style_rag = providers.Singleton(
        "src.backend.engine_style_rag.StyleRagManager", client=genai_client, repo=repo
    )
    writer = providers.Singleton(
        "src.agents.writing.WritingAgent",
        repo=repo,
        llm=llm,
        prompt_manager=pm,
        style_rag=style_rag,
        plot_expander=plot_expander,
    )
    formatter = providers.Singleton("src.backend.sanitizer.TextFormatter")
    # PlanningService: 企画・プロット生成を担当 (ADR-0004)
    planning_service = providers.Factory(
        "src.backend.planning_service.PlanningService",
        bible_generator=bible_generator,
        repo=repo,
        pm=pm,
        ctx_mgr=ctx_mgr,
        reporter_factory=reporter_factory,
    )
    # WritingService: 本文�執�筆・研�磨を担当 (ADR-0004)
    writing_service = providers.Factory(
        "src.backend.writing_service.WritingService",
        writer=writer,
        repo=repo,
        pm=pm,
        style_rag=style_rag,
        ctx_mgr=ctx_mgr,
        reporter_factory=reporter_factory,
    )
    engine = providers.Factory(
        "src.backend.engine.UltimateHegemonyEngine",
        api_key=api_key,
        planner=planner,
        writer=writer,
        repo=repo,
        db=db,
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
    )
    engine_facade = providers.Factory(
        "src.backend.engine_facade.EngineFacade",
        config=providers.Factory(EngineConfig.create, api_key=api_key, cooldown=cooldown),
        engine=engine,
    )
    redis_cache = providers.Factory("src.services.redis_cache.RedisCacheService")
    prompt_cache = providers.Factory(
        "src.services.redis_cache.PromptCacheService",
        redis_cache=redis_cache,
        semantic_cache=None,
        l1_cache=None,
    )

Container = AppContainer