from __future__ import annotations

import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError, OperationalError

from src.services.age_client import (
    AgeClient,
    CypherResult,
    GraphStats,
    _parse_agtype,
    _interpolate_cypher_params,
    _dict_to_cypher_map,
    _sanitize_graph_name,
    _validate_column_def,
    _is_retryable_db_error,
)

# ==============================================================================
# 1. Utility Function Tests
# ==============================================================================

class TestAgeClientUtils:
    def test_parse_agtype(self):
        # Basic types
        assert _parse_agtype(None) is None
        assert _parse_agtype(123) == 123
        assert _parse_agtype(True) is True
        
        # agtype strings
        assert _parse_agtype('{"key": "val"}') == {"key": "val"}
        assert _parse_agtype('[1, 2, 3]') == [1, 2, 3]
        
        # Vertex/Edge suffixes
        assert _parse_agtype('"Hero"::vertex') == "Hero"
        assert _parse_agtype('"Sword"::edge') == "Sword"
        
        # Invalid JSON should return string
        assert _parse_agtype("not json") == "not json"

    def test_interpolate_cypher_params(self):
        query = "MATCH (n) WHERE n.name = $name AND n.age = $age AND n.active = $active"
        params = {
            "name": "O'Connor",
            "age": 25,
            "active": True
        }
        result = _interpolate_cypher_params(query, params)
        assert "n.name = 'O''Connor'" in result
        assert "n.age = 25" in result
        assert "n.active = true" in result

    def test_interpolate_cypher_params_complex(self):
        query = "MATCH (n) SET n.props = $props, n.tags = $tags, n.meta = $meta"
        params = {
            "props": {"level": 10, "rank": "S"},
            "tags": ["hero", "legend"],
            "meta": None
        }
        result = _interpolate_cypher_params(query, params)
        assert 'n.props = {"level": 10, "rank": "S"}' in result
        assert 'n.tags = ["hero", "legend"]' in result
        assert "n.meta = null" in result

    def test_dict_to_cypher_map(self):
        d = {"name": "Hero", "level": 10, "is_active": True, "meta": None, "tags": ["a", "b"]}
        result = _dict_to_cypher_map(d)
        assert result.startswith("{") and result.endswith("}")
        assert "name: 'Hero'" in result
        assert "level: 10" in result
        assert "is_active: true" in result
        assert "meta: null" in result
        assert 'tags: ["a", "b"]' in result

    def test_sanitize_graph_name(self):
        assert _sanitize_graph_name("my_graph_123") == "my_graph_123"
        with pytest.raises(ValueError, match="Invalid graph name"):
            _sanitize_graph_name("my-graph!")

    def test_validate_column_def(self):
        assert _validate_column_def("(result agtype)") == "(result agtype)"
        assert _validate_column_def("(name agtype, age int)") == "(name agtype, age int)"
        with pytest.raises(ValueError, match="Invalid column definition format"):
            _validate_column_def("invalid_format")
        with pytest.raises(ValueError, match="Invalid column definition format"):
            _validate_column_def("(result; agtype)")

    def test_is_retryable_db_error(self):
        # Mock an exception with pgcode
        mock_exc = MagicMock(spec=OperationalError)
        mock_exc.orig = MagicMock()
        mock_exc.orig.pgcode = "40001" # serialization_failure
        assert _is_retryable_db_error(mock_exc) is True
        
        mock_exc.orig.pgcode = "00000" # success/unknown
        assert _is_retryable_db_error(mock_exc) is False
        
        # Non-DB error
        assert _is_retryable_db_error(ValueError("test")) is False

# ==============================================================================
# 2. AgeClient Core Tests
# ==============================================================================

class TestAgeClient:
    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        # Default return for execute() is a list of rows (each row is a tuple-like)
        # We'll set this per test as needed
        session.execute.return_value = []
        return session

    def test_init_graph_success(self, mock_session):
        client = AgeClient(default_graph_name="test_graph")
        success = client.init_graph(mock_session)
        assert success is True
        assert client._initialized is True
        # Verify SQL
        calls = [str(call.args[0]) for call in mock_session.execute.call_args_list]
        assert any("create_graph('test_graph')" in c for c in calls)

    def test_init_graph_already_exists(self, mock_session):
        client = AgeClient(default_graph_name="test_graph")
        
        # First call to create_graph fails with duplicate_graph (42P04)
        # Second call to check existence succeeds
        mock_err = ProgrammingError("duplicate", None, None)
        mock_err.orig = MagicMock(pgcode="42P04")
        
        # Sequence: 1. LOAD, 2. SET, 3. create_graph (FAIL), 4. check exists (SUCCESS)
        mock_session.execute.side_effect = [
            None, None, mock_err, MagicMock(first=lambda: MagicMock(scalar=lambda: 1))
        ]
        
        success = client.init_graph(mock_session)
        assert success is True
        assert client._initialized is True

    def test_execute_cypher(self, mock_session):
        client = AgeClient(default_graph_name="test_graph")
        
        # Mock result records: each row is a MagicMock with _mapping attribute (SQLAlchemy 2.0 style)
        mock_row = MagicMock()
        mock_row._mapping = {"result": '{"name": "Hero", "level": 10}'}
        mock_session.execute.return_value = [mock_row]
        
        res = client.execute_cypher(
            mock_session, 
            "MATCH (n) RETURN n", 
            parameters={"name": "Hero"}
        )
        
        assert isinstance(res, CypherResult)
        assert len(res.records) == 1
        assert res.records[0]["result"] == {"name": "Hero", "level": 10}
        
        # Verify interpolation
        last_sql = str(mock_session.execute.call_args[0][0])
        assert "cypher('test_graph'" in last_sql

    def test_execute_cypher_streaming(self, mock_session):
        client = AgeClient(default_graph_name="test_graph")
        
        # Mock 5 records - each row is a MagicMock with _mapping attribute
        mock_rows = []
        for i in range(5):
            row = MagicMock()
            row._mapping = {"result": f'{{"id": {i}}}'}
            mock_rows.append(row)
        mock_session.execute.return_value = mock_rows
        
        # Batch size 2 -> should yield 3 batches (2, 2, 1)
        batches = list(client.execute_cypher_streaming(mock_session, "MATCH (n) RETURN n", batch_size=2))
        
        assert len(batches) == 3
        assert len(batches[0]) == 2
        assert len(batches[1]) == 2
        assert len(batches[2]) == 1
        assert batches[0][0]["result"] == {"id": 0}

    def test_upsert_node(self, mock_session):
        client = AgeClient(default_graph_name="test_graph")
        success = client.upsert_node(
            mock_session, 
            label="Character", 
            name="Hero", 
            properties={"level": 10}
        )
        assert success is True
        sql = str(mock_session.execute.call_args[0][0])
        assert "MERGE (n:Character {name: 'Hero'})" in sql
        assert "SET n += {level: 10, name: 'Hero'}" in sql

    def test_upsert_nodes_batch(self, mock_session):
        client = AgeClient(default_graph_name="test_graph")
        nodes = [
            {"label": "Character", "name": "Hero", "properties": {"level": 10}},
            {"label": "Item", "name": "Sword", "properties": {"power": 100}},
            {"label": "Character", "name": "", "properties": {}}, # Should be skipped
        ]
        count = client.upsert_nodes_batch(mock_session, nodes)
        assert count == 2
        assert mock_session.execute.call_count >= 2

    def test_upsert_edge(self, mock_session):
        client = AgeClient(default_graph_name="test_graph")
        success = client.upsert_edge(
            mock_session,
            source_label="Character", source_name="Hero",
            target_label="Item", target_name="Sword",
            relation_type="owns",
            properties={"since": "2023"}
        )
        assert success is True
        sql = str(mock_session.execute.call_args[0][0])
        assert "MATCH (a:Character {name: 'Hero'}), (b:Item {name: 'Sword'})" in sql
        assert "MERGE (a)-[r:OWNS]->(b)" in sql
        assert "SET r += {since: '2023'}" in sql

    def test_get_neighbors(self, mock_session):
        client = AgeClient(default_graph_name="test_graph")
        
        # Mock result: 2 neighbors - each row is a tuple of 4 elements
        mock_row1 = ('"Neighbor1"', '["Label1"]', '{"prop": "val1"}', '"RELATED_TO"')
        mock_row2 = ('"Neighbor2"', '["Label2"]', '{"prop": "val2"}', '"OWNS"')
        
        mock_session.execute.return_value = [mock_row1, mock_row2]
        
        neighbors = client.get_neighbors(mock_session, "Hero", max_depth=2)
        assert len(neighbors) == 2
        assert neighbors[0]["name"] == "Neighbor1"  # stripped quotes
        assert neighbors[0]["relation_type"] == "RELATED_TO"
        assert neighbors[1]["name"] == "Neighbor2"  # stripped quotes
        assert neighbors[1]["relation_type"] == "OWNS"

    def test_get_shortest_path(self, mock_session):
        client = AgeClient(default_graph_name="test_graph")
        
        # Mock path result - need to mock fetchone() call
        mock_result = MagicMock()
        mock_row = ('{"nodes": ["Hero", "Sword"], "edges": ["owns"]}',)
        mock_result.fetchone.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        path = client.get_shortest_path(mock_session, "Hero", "Sword")
        assert path is not None
        assert path["nodes"] == ["Hero", "Sword"]

    def test_delete_node_and_edge(self, mock_session):
        client = AgeClient(default_graph_name="test_graph")
        
        # Delete node
        assert client.delete_node(mock_session, "Character", "Hero") is True
        sql_node = str(mock_session.execute.call_args[0][0])
        assert "DETACH DELETE n" in sql_node
        
        # Delete edge
        assert client.delete_edge(mock_session, "Character", "Hero", "Item", "Sword", "owns") is True
        sql_edge = str(mock_session.execute.call_args[0][0])
        assert "DELETE r" in sql_edge

    def test_get_graph_stats(self, mock_session):
        client = AgeClient(default_graph_name="test_graph")
        
        # Mock psycopg2.connect
        with patch("psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_connect.return_value.__enter__.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur
            
            # Mock results for node_count, edge_count, labels, rel_types
            mock_cur.fetchone.return_value = ('100',)
            mock_cur.fetchall.side_effect = [
                [("Label1",), ("Label2",)], # labels
                [("REL1",), ("REL2",)],     # rel_types
            ]
            
            # We need to mock the session bind to get the URL
            mock_bind = MagicMock()
            mock_bind.url = MagicMock(host="localhost", port=5432, database="testdb", username="user", password="pass")
            mock_session.get_bind.return_value = mock_bind
            
            stats = client.get_graph_stats(mock_session)
            
            assert stats.node_count == 100
            assert "Label1" in stats.labels
            assert "REL1" in stats.relationship_types

    def test_check_entity_validity(self, mock_session):
        client = AgeClient(default_graph_name="test_graph")
        
        # Case 1: Valid entity
        mock_result = MagicMock()
        mock_row = ("false", "false", '"active"')  # is_forbidden, is_retired, status
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        res = client.check_entity_validity(mock_session, "test_graph", "Hero")
        assert res["valid"] is True
        assert res["status"] == "active"
        
        # Case 2: Forbidden entity
        mock_row_forbidden = ("true", "false", '"forbidden"')
        mock_result_forbidden = MagicMock()
        mock_result_forbidden.first.return_value = mock_row_forbidden
        mock_session.execute.return_value = mock_result_forbidden
        
        res = client.check_entity_validity(mock_session, "test_graph", "Villain")
        assert res["valid"] is False
        assert res["is_forbidden"] is True

    def test_conflict_checks(self, mock_session):
        client = AgeClient(default_graph_name="test_graph")
        
        # Temporal conflict: min_ts > max_ts
        mock_result = MagicMock()
        mock_row = ("100", "50")  # min_ts, max_ts
        mock_result.first.return_value = mock_row
        mock_session.execute.return_value = mock_result
        
        conflicts = client._check_temporal_conflicts(mock_session, "test_graph", "Hero")
        assert "temporal_reversed" in conflicts

# ==============================================================================
# 3. Retry Logic Tests
# ==============================================================================

def test_safe_retry_mechanism():
    # We want to test that @_safe_retry actually retries on specific exceptions
    # Since _safe_retry is a decorator, we can test it by applying it to a dummy function
    
    from src.services.age_client import _safe_retry
    
    call_count = 0
    @_safe_retry(max_attempts=3)
    def unstable_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            # Raise a retryable error
            raise OperationalError("retry me", None, None)
        return "success"
    
    assert unstable_func() == "success"
    assert call_count == 3

def test_safe_retry_failure():
    from src.services.age_client import _safe_retry
    
    call_count = 0
    @_safe_retry(max_attempts=2)
    def failing_func():
        nonlocal call_count
        call_count += 1
        raise OperationalError("fail", None, None)
    
    with pytest.raises(OperationalError):
        failing_func()
    assert call_count == 2