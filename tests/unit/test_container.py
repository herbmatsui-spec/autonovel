from dependency_injector import providers

from src.core.container import AppContainer


def test_container_wiring():
    container = AppContainer()
    container.api_key.override("dummy_key")

    repo = container.repo()
    assert repo is not None

    db = container.db()
    assert db is not None

    llm = container.llm()
    assert llm is not None

    planner = container.planner()
    assert planner is not None

    writer = container.writer()
    assert writer is not None


def test_all_providers_resolved():
    container = AppContainer()
    container.api_key.override("dummy_key")

    expected_providers = [
        "api_key",
        "db",
        "vector_store",
        "audit_logger",
        "cooldown",
        "genai_client",
        "llm_factory",
        "semantic_cache",
        "edge_preserver",
        "llm",
        "connection_pipeline",
        "repo",
        "uow",
        "pm",
        "ctx_mgr",
        "global_config",
        "auditor",
        "marketing",
        "bible_generator",
        "plot_expander",
        "planner",
        "validator",
        "narrative",
        "critique",
        "style_rag",
        "writer",
        "formatter",
        "engine",
        "engine_facade",
    ]

    missing = []
    failures = []

    for p_name in expected_providers:
        if not hasattr(container, p_name):
            missing.append(p_name)
            continue
        provider = getattr(container, p_name)
        try:
            if isinstance(provider, providers.Singleton):
                instance = provider()
            elif isinstance(provider, providers.Factory):
                instance = provider()
            elif isinstance(provider, providers.Object):
                instance = provider()
            else:
                instance = provider()
        except Exception as e:
            failures.append(f"{p_name}: {type(e).__name__}: {e}")

    assert not missing, f"Missing providers: {missing}"
    assert not failures, f"Resolution failures: {failures}"
