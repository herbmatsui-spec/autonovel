import pytest

from src.core.container.infra import InfraContainer


def test_infra_container_providers_resolved():
    container = InfraContainer()

    providers_to_test = [
        "config",
        "global_config",
        "db",
        "chroma_client_provider",
        "vector_store",
        "audit_logger",
        "cooldown",
    ]

    for p_name in providers_to_test:
        assert hasattr(container, p_name), f"Missing provider: {p_name}"
        provider = getattr(container, p_name)
        try:
            instance = provider()
        except Exception as e:
            pytest.fail(f"Provider {p_name} raised {type(e).__name__}: {e}")
