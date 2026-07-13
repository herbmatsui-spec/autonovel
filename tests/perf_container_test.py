import pytest

from src.core.container import AppContainer


def test_container_initialization_and_resolution():
    """
    Verify that all providers in AppContainer can be resolved without causing 
    circular reference errors or initialization failures.
    """
    container = AppContainer()

    # List of providers to resolve to check for circularity/init errors
    providers_to_test = [
        "api_key", "db", "vector_store", "audit_logger", "cooldown",
        "genai_client", "llm_factory", "semantic_cache", "llm",
        "connection_pipeline", "repo", "uow", "pm", "ctx_mgr", "global_config",
        "audit_service_factory", "auditor", "marketing", "bible_generator",
        "plot_expander", "planner", "validator", "narrative", "critique",
        "style_rag", "writer", "formatter"
    ]

    resolved_instances = {}

    for p_name in providers_to_test:
        try:
            provider = getattr(AppContainer, p_name)
            # Resolve the provider (handle both Singleton/Factory/Object providers)
            instance = provider()
            resolved_instances[p_name] = instance
        except Exception as e:
            pytest.fail(f"Failed to resolve provider '{p_name}': {e}")

    assert len(resolved_instances) == len(providers_to_test)
