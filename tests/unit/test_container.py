from src.core.container import AppContainer


def test_container_wiring():
    container = AppContainer()
    container.api_key.override("dummy_key")

    # Try resolving key components
    repo = container.repo()
    assert repo is not None

    db = container.db()
    assert db is not None

    # Ensure LLM client resolves
    llm = container.llm()
    assert llm is not None

    # Check agents
    planner = container.planner()
    assert planner is not None

    writer = container.writer()
    assert writer is not None

    # Mediator has been removed in v3.0
