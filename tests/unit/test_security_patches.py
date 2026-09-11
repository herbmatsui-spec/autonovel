"""
Unit tests verifying Phase 2 security patches:
- Cypher query & column definition validation (SQL injection prevention)
- Admin endpoint authentication enforcement
"""
import pytest
from pydantic import ValidationError
from src.backend.routers.graph import CypherQueryRequest, router as graph_router
from src.backend.routers.system import router as system_router
from src.backend.auth import require_api_key
from src.services.age_client import _sanitize_graph_name, _validate_column_def


def test_cypher_query_request_valid():
    """Valid column definition should be accepted."""
    req = CypherQueryRequest(query="MATCH (n) RETURN n", column_definition="(result agtype)")
    assert req.column_definition == "(result agtype)"

    req_multi = CypherQueryRequest(
        query="MATCH (n) RETURN n.id, n.name",
        column_definition="(id agtype, name agtype)"
    )
    assert req_multi.column_definition == "(id agtype, name agtype)"


def test_cypher_query_request_sql_injection_rejection():
    """SQL injection attempts in column_definition must be rejected."""
    injections = [
        "(result agtype); DROP TABLE users; --",
        "(result agtype) -- comment",
        "(result agtype) /* comment */",
        "result agtype",  # missing parens
        "(res agtype) $$ SELECT 1",
    ]
    for inj in injections:
        with pytest.raises(ValidationError):
            CypherQueryRequest(query="MATCH (n) RETURN n", column_definition=inj)


def test_age_client_sanitization_helpers():
    """AgeClient sanitizers should accept valid inputs and reject malicious ones."""
    assert _sanitize_graph_name("knowledge_graph_1") == "knowledge_graph_1"
    with pytest.raises(ValueError):
        _sanitize_graph_name("graph; DROP TABLE books;")
    with pytest.raises(ValueError):
        _sanitize_graph_name("graph name with spaces")

    assert _validate_column_def("(res agtype)") == "(res agtype)"
    with pytest.raises(ValueError):
        _validate_column_def("(res agtype); --")


def test_graph_cypher_endpoint_has_auth_dependency():
    """The /api/graph/cypher endpoint must require an API key."""
    route = next(r for r in graph_router.routes if getattr(r, "path", None) == "/api/graph/cypher")
    dep_calls = [d.dependency for d in route.dependencies]
    assert require_api_key in dep_calls, "require_api_key must be enforced on /api/graph/cypher"


def test_system_admin_endpoints_have_auth_dependencies():
    """All /admin/ endpoints in system router must require an API key."""
    admin_routes = [r for r in system_router.routes if "/admin/" in getattr(r, "path", "")]
    assert len(admin_routes) >= 6, f"Expected at least 6 admin routes, got {len(admin_routes)}"

    for r in admin_routes:
        dep_calls = [d.dependency for d in r.dependencies]
        assert require_api_key in dep_calls, f"Route {r.path} missing require_api_key dependency"
