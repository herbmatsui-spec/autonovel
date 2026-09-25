"""AgeClient graph operations coverage: upsert, batch, neighbors, path, delete, stats."""
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text

from src.services.age_client import AgeClient, GraphStats, _parse_agtype


def make_client(default_graph="novel_graph"):
    client = AgeClient.__new__(AgeClient)
    client.default_graph_name = default_graph
    return client


def make_session(pg_dialect="postgresql"):
    session = MagicMock()
    bind = MagicMock()
    bind.dialect.name = pg_dialect
    session.get_bind.return_value = bind
    return session


# ============================================================================
# upsert_edge
# ============================================================================


def test_upsert_edge_success():
    client = make_client()
    session = make_session()
    assert client.upsert_edge(session, "Entity", "A", "Entity", "B", "related_to",
                              properties={"weight": 1}) is True
    sql = str(session.execute.call_args[0][0])
    assert "MATCH (a:Entity {name: 'A'})" in sql
    assert "MERGE (a)-[r:RELATED_TO]->(b)" in sql
    assert "SET r += {weight: 1}" in sql
    assert sql.startswith("SELECT * FROM cypher('novel_graph'")


def test_upsert_edge_failure_returns_false():
    client = make_client()
    session = make_session()
    session.execute.side_effect = RuntimeError("db down")
    assert client.upsert_edge(session, "Entity", "A", "Entity", "B", "REL") is False


def test_upsert_edge_invalid_label_raises():
    client = make_client()
    session = make_session()
    with pytest.raises(ValueError, match="Invalid label"):
        client.upsert_edge(session, "!!!", "A", "Entity", "B", "REL")


# ============================================================================
# upsert_edges_batch
# ============================================================================


def test_upsert_edges_batch_counts_successes():
    client = make_client()
    session = make_session()
    session.execute.side_effect = lambda *a, **k: None
    edges = [
        {"source_name": "A", "target_name": "B"},
        {"source_name": None, "target_name": "B"},  # skipped: missing name
        {"source_label": "!!!", "source_name": "A", "target_name": "B"},  # skipped: invalid label
        {"source_name": "C", "target_name": "D", "relation_type": "knows",
         "properties": {"since": 2020}},
    ]
    count = client.upsert_edges_batch(session, edges)
    assert count == 2  # 2 valid edges executed
    sql = str(session.execute.call_args[0][0])
    assert "KNOWS" in sql


@pytest.mark.parametrize("relation_type,expected", [
    ("related-to", "RELATED_TO"),
    ("knows", "KNOWS"),
    ("my rel!", "MY_REL_"),
])
def test_upsert_edge_relation_type_sanitization(relation_type, expected):
    client = make_client()
    session = make_session()
    client.upsert_edge(session, "Entity", "A", "Entity", "B", relation_type)
    sql = str(session.execute.call_args[0][0])
    assert f"[r:{expected}]" in sql


def test_upsert_edges_batch_failure_is_non_fatal():
    client = make_client()
    session = make_session()
    session.execute.side_effect = RuntimeError("db down")
    edges = [{"source_name": "A", "target_name": "B"}]
    assert client.upsert_edges_batch(session, edges) == 0


# ============================================================================
# get_all_nodes
# ============================================================================


def test_get_all_nodes_non_postgresql_returns_empty():
    client = make_client()
    session = make_session(pg_dialect="sqlite")
    assert client.get_all_nodes(session) == []


def test_get_all_nodes_success_with_labels():
    client = make_client()
    session = make_session()
    result = MagicMock()
    result.__iter__ = MagicMock(return_value=iter([
        ('"Hero"', '["Entity"]', '{"level": 10}'),
        (None, "", None),
    ]))
    session.execute.return_value = result
    rows = client.get_all_nodes(session, labels=["Entity"], limit=100)
    assert rows[0]["name"] == "Hero"
    assert rows[0]["properties"] == {"level": 10}
    assert rows[1]["name"] == ""


def test_get_all_nodes_error_returns_empty():
    client = make_client()
    session = make_session()
    session.execute.side_effect = RuntimeError("db")
    assert client.get_all_nodes(session) == []
    session.rollback.assert_called_once()


# ============================================================================
# get_neighbors
# ============================================================================


def test_get_neighbors_directions_and_filters():
    client = make_client()
    for direction, arrow in (("outgoing", "->"), ("incoming", "<-"), ("both", "-")):
        session = make_session()
        result = MagicMock()
        result.__iter__ = MagicMock(return_value=iter([
            ('"B"', '["Entity"]', '{"w": 1}', '"RELATED_TO"'),
        ]))
        session.execute.return_value = result
        neighbors = client.get_neighbors(session, "A", max_depth=2,
                                         relationship_types=["related_to"],
                                         direction=direction)
        assert neighbors[0]["name"] == "B"
        assert neighbors[0]["relation_type"] == "RELATED_TO"
        sql = str(session.execute.call_args[0][0])
        assert arrow in sql


def test_get_neighbors_single_depth():
    client = make_client()
    session = make_session()
    result = MagicMock()
    result.__iter__ = MagicMock(return_value=iter([]))
    session.execute.return_value = result
    assert client.get_neighbors(session, "A", max_depth=1) == []
    sql = str(session.execute.call_args[0][0])
    assert "*1]" in sql or "1]" in sql


def test_get_neighbors_error_returns_empty():
    client = make_client()
    session = make_session()
    session.execute.side_effect = RuntimeError("db")
    assert client.get_neighbors(session, "A") == []


# ============================================================================
# get_shortest_path
# ============================================================================


def test_get_shortest_path_found():
    client = make_client()
    session = make_session()
    result = MagicMock()
    result.fetchone.return_value = ['[{"start": 1}]']
    session.execute.return_value = result
    path = client.get_shortest_path(session, "A", "B")
    assert path == [{"start": 1}]


def test_get_shortest_path_not_found_and_error():
    client = make_client()
    session = make_session()
    result = MagicMock()
    result.fetchone.return_value = None
    session.execute.return_value = result
    assert client.get_shortest_path(session, "A", "B") is None

    session.execute.side_effect = RuntimeError("db")
    assert client.get_shortest_path(session, "A", "B") is None


# ============================================================================
# delete_node / delete_edge
# ============================================================================


@pytest.mark.parametrize("detach,expected_cypher", [
    (True, "DETACH DELETE"),
    (False, "DELETE"),
])
def test_delete_node_detach_variations(detach, expected_cypher):
    client = make_client()
    session = make_session()
    assert client.delete_node(session, "Entity", "A", detach=detach) is True
    sql = str(session.execute.call_args[0][0])
    assert expected_cypher in sql
    assert "MATCH (n:Entity {name: 'A'})" in sql


def test_delete_node_invalid_label_and_error():
    client = make_client()
    session = make_session()
    with pytest.raises(ValueError, match="Invalid label"):
        client.delete_node(session, "", "A")
    session.execute.side_effect = RuntimeError("db")
    assert client.delete_node(session, "Entity", "A") is False


def test_delete_edge_success_invalid_and_error():
    client = make_client()
    session = make_session()
    assert client.delete_edge(session, "Entity", "A", "Entity", "B", "REL") is True
    with pytest.raises(ValueError, match="Invalid label"):
        client.delete_edge(session, "!!!", "A", "Entity", "B", "REL")
    session.execute.side_effect = RuntimeError("db")
    assert client.delete_edge(session, "Entity", "A", "Entity", "B", "REL") is False


# ============================================================================
# get_graph_stats
# ============================================================================


def test_get_graph_stats_no_bind():
    client = make_client()
    session = MagicMock()
    session.get_bind.return_value = None
    stats = client.get_graph_stats(session)
    assert stats == GraphStats(node_count=0, edge_count=0, labels=[], relationship_types=[])


def test_get_graph_stats_no_engine():
    client = make_client()
    session = make_session()
    session.get_bind.return_value = MagicMock(spec=["dialect"])  # no url/engine
    stats = client.get_graph_stats(session)
    assert stats.node_count == 0
    assert stats.edge_count == 0


# ============================================================================
# Utility edge cases
# ============================================================================


def test_parse_agtype_edge_cases():
    assert _parse_agtype("") == ""
    assert _parse_agtype('"plain"::vertex') == "plain"
    assert _parse_agtype('"p"::edge') == "p"
