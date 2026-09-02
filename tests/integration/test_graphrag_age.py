"""Apache AGE (GraphRAG) 実環境テスト.

testcontainers-python で apache/age-postgresql:16-pgvector イメージを使い、
実際の Cypher クエリ動作を検証する。Docker 未起動 / testcontainers 未導入の
環境では自動的に skip される。
"""
from __future__ import annotations

import socket

import pytest

try:
    from testcontainers.postgres import PostgresContainer

    _HAS_TESTCONTAINERS = True
except Exception:
    _HAS_TESTCONTAINERS = False


def _docker_available() -> bool:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.close()
        return True
    except Exception:
        pass
    try:
        s = socket.create_connection(("localhost", 2375), timeout=0.5)
        s.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (_HAS_TESTCONTAINERS and _docker_available()),
    reason="testcontainers / Docker daemon not available",
)


@pytest.fixture(scope="module")
def age_container():
    """apache/age-postgresql:16-pgvector を起動し SQLAlchemy engine を返す."""
    from sqlalchemy import create_engine

    container = PostgresContainer("apache/age-postgresql:16-pgvector")
    container.start()
    url = container.get_connection_url()
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()
        container.stop()


def test_age_init_graph_idempotent(age_container):
    """init_graph を 2 回呼んでも両方 True でグラフ重複作成エラーにならない."""
    from sqlalchemy.orm import sessionmaker

    from src.services.age_client import AgeClient

    Session = sessionmaker(bind=age_container)
    session = Session()
    client = AgeClient(default_graph_name="test_graph_idem")
    try:
        assert client.init_graph(session) is True
        assert client.init_graph(session) is True
    finally:
        session.close()


def test_age_upsert_node_dedup(age_container):
    """同じ (label, name) で 2 回 upsert_node してもノードは 1 つだけ."""
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from src.services.age_client import AgeClient

    Session = sessionmaker(bind=age_container)
    session = Session()
    client = AgeClient(default_graph_name="test_graph_dedup")
    try:
        assert client.init_graph(session) is True
        assert client.upsert_node(session, "Character", "アルス", {"age": 20}) is True
        assert client.upsert_node(session, "Character", "アルス", {"age": 21}) is True

        cnt = session.execute(
            text(
                "SELECT count(*)::text FROM cypher('test_graph_dedup', "
                "$$ MATCH (n:Character {name: 'アルス'}) RETURN n $$) as (c agtype);"
            )
        ).scalar()
        assert int(str(cnt).strip('"')) == 1
    finally:
        session.close()


def test_age_sqlstate_duplicate_graph_returns_true(age_container):
    """pgcode 42P04 (duplicate_graph) が出ても init_graph は True を返す (SQLSTATE ベース)."""
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    from src.services.age_client import AgeClient

    Session = sessionmaker(bind=age_container)
    session = Session()
    client = AgeClient(default_graph_name="test_graph_pgcode")
    try:
        assert client.init_graph(session) is True
        # 2 回目の init_graph は pgcode 42P04 を起こすはずだが True 扱い
        assert client.init_graph(session) is True
        # 念のため直接 drop して存在確認
        session.execute(text('SET search_path = ag_catalog, "$user", public;'))
        rows = session.execute(
            text("SELECT name FROM ag_graph WHERE name = 'test_graph_pgcode';")
        ).fetchall()
        assert any(r[0] == "test_graph_pgcode" for r in rows)
    finally:
        session.close()
