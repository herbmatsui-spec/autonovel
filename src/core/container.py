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
from src.backend.engine_context import ContextManager
from src.core.llm_gateway import (
    LLMGenerateResultProxy,  # noqa: F401  (テスト互換のため再エクスポート)
)

logger = logging.getLogger(__name__)


class AppContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=["src"]
    )

    # 外部入力 (起動時に上書き可能)
    api_key = providers.Object("DUMMY")

    # インフラ
    db = providers.Singleton(get_db_manager)
    vector_store = providers.Singleton(lambda: None)  # ChromaVectorStore 必要に応じて差し替え
    audit_logger = providers.Singleton(lambda: None)
    cooldown = providers.Singleton(
        "src.backend.engine_utils.AdaptiveCooldown",
        base_sec=2.0,
        min_sec=0.5,
        max_sec=10.0
    )
    genai_client = providers.Singleton(
        "src.core.llm_gateway.create_genai_client",
        api_key=api_key
    )
    llm_factory = providers.Singleton(
        "src.core.llm_gateway.LLMProviderFactory",
        genai_client=genai_client,
        cooldown=cooldown
    )
    semantic_cache = providers.Singleton(
        "src.core.llm_gateway.SemanticCacheManager",
        vector_store=vector_store
    )
    edge_preserver = providers.Singleton(
        "src.backend.sharp_edge_preserver.SemanticEdgePreserver",
        semantic_cache=semantic_cache,
        similarity_threshold=0.75,
        use_semantic=True,
    )
    llm = providers.Singleton(
        "src.core.llm_gateway.LLMGenerateResultProxy",
        llm_factory=llm_factory
    )
    connection_pipeline = providers.Singleton(
        lambda: None  # デフォルトはパススルー
    )

    # データアクセス
    repo = providers.Singleton(
        DataRepository,
        db=db
    )
    uow = providers.Factory(
        UnitOfWork,
        db=db
    )

    # Prompt管理
    pm = providers.Singleton(PromptManager)

    # 設定
    ctx_mgr = providers.Singleton(
        ContextManager,
        repo=repo
    )
    global_config = providers.Singleton(get_config)

    # エージェント・サービス
    auditor = providers.Singleton(
        "src.agents.LogicalAuditor",
        repo=repo,
        pm=pm,
        llm=llm,
        ctx_mgr=ctx_mgr
    )
    marketing = providers.Singleton(
        "src.agents.MarketingAgent",
        repo=repo,
        prompt_manager=pm,
        llm=llm
    )
    bible_generator = providers.Singleton(
        "src.services.bible_service.WorldBibleGenerator",
        repo=repo,
        llm=llm,
        pm=pm,
        debate=None,
        marketing=marketing,
        auditor=auditor
    )
    plot_expander = providers.Singleton(
        "src.agents.plot.PlotAgent",
        repo=repo,
        pm=pm,
        generate_json=llm.provided.generate_json
    )
    planner = providers.Singleton(
        "src.agents.PlanningAgent",
        repo=repo,
        llm=llm,
        prompt_manager=pm
    )
    validator = providers.Singleton(
        "src.agents.LogicalAuditor",
        repo=repo,
        pm=pm,
        llm=llm,
        ctx_mgr=ctx_mgr
    )
    narrative = providers.Singleton(
        "src.backend.engine_narrative.NarrativeController",
        repo=repo,
        pm=pm,
        ctx_mgr=ctx_mgr,
        generate_json=llm.provided.generate_json,
        logic_validator=validator,
        auditor=auditor
    )
    critique = providers.Singleton(
        "src.backend.engine_critique.CritiqueAgent",
        repo=repo,
        pm=pm,
        generate_json=llm.provided.generate_json
    )
    style_rag = providers.Singleton(
        "src.backend.engine_style_rag.StyleRagManager",
        client=genai_client,
        repo=repo
    )
    writer = providers.Singleton(
        "src.agents.WritingAgent",
        repo=repo,
        llm=llm,
        prompt_manager=pm,
        style_rag=style_rag
    )
    formatter = providers.Singleton(
        "src.backend.sanitizer.TextFormatter"
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
        style_rag=style_rag,
        llm=llm,
        cooldown=cooldown
    )
