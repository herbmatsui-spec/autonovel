import pytest
from src.services.graph.networkx_store import NetworkXGraphStore
from src.services.cost_budget_guard import CostBudgetGuard
from src.agents.specialists.model_router import AuditorModelRouter


def test_networkx_graph_store_regression():
    store = NetworkXGraphStore()
    store.add_entity("Character", "アリス", {"role": "protagonist"})
    store.add_entity("Character", "ボブ", {"role": "ally"})
    store.add_relation("Character", "アリス", "Character", "ボブ", "FRIEND")

    neighbors = store.find_neighbors("アリス", hops=1)
    assert len(neighbors.nodes) >= 1
    assert any(n.name == "ボブ" for n in neighbors.nodes)


def test_cost_budget_guard_regression():
    from src.services.cost_analytics import CostCalculator
    calc = CostCalculator()
    guard = CostBudgetGuard(calculator=calc, budget_limit=10.0)
    status = guard.check_budget_status(book_id=1)
    assert status.value in ("normal", "warning", "exceeded")


def test_auditor_model_router_regression():
    router = AuditorModelRouter()
    provider = router._resolve_primary_provider_for_auditor("consistency")
    assert provider in ("gemini", "openai", "claude")
