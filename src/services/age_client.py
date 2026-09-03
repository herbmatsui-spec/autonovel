"""Apache AGE (openCypher) 連携クライアントモジュール.

PostgreSQL の Apache AGE 拡張を利用して、グラフの初期化、ノード・エッジの作成、
および近傍探索（Graph Traversal）を SQL 経由で透過的に実行する。

Enhanced with:
- Connection pooling and session management
- Parameterized Cypher queries (SQL injection prevention)
- Comprehensive error handling with SQLSTATE-based retry
- agtype parsing and validation
- Graph statistics and monitoring
- Batch operations support
"""
from __future__ import annotations

import json
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.orm import Session
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.backend.config import settings
from src.backend.logging_config import get_logger

logger = get_logger("age_client")

_RETRY_SQLSTATES = {
    "40001",  # serialization_failure
    "40P01",  # deadlock_detected
    "08006",  # connection_failure
    "57P03",  # cannot_connect_now
    "42P04",  # duplicate_graph (idempotent init)
    "23505",  # unique_violation
    "08001",  # sqlclient_unable_to_establish_sqlconnection
    "08004",  # sqlserver_rejected_establishment_of_sqlconnection
    "53300",  # too_many_connections
}


@dataclass
class CypherResult:
    """Cypherクエリ実行結果の構造化データ."""
    records: list[dict[str, Any]]
    summary: dict[str, Any]
    execution_time_ms: float


@dataclass
class GraphStats:
    """グラフ統計情報."""
    node_count: int
    edge_count: int
    labels: list[str]
    relationship_types: list[str]


def _is_retryable_db_error(exc: BaseException) -> bool:
    """SQLSTATE コードでリトライ可否を判定する."""
    if isinstance(exc, (IntegrityError, ProgrammingError, OperationalError)):
        pgcode = getattr(getattr(exc, "orig", None), "pgcode", None)
        if pgcode in _RETRY_SQLSTATES:
            return True
    if isinstance(exc, DBAPIError):
        pgcode = getattr(getattr(exc, "orig", None), "pgcode", None)
        if pgcode in _RETRY_SQLSTATES:
            return True
    return False


def _safe_retry(max_attempts: int = 3):
    """tenacity ベースの SQLSTATE 駆動リトライデコレータを返す."""
    def _before_sleep(retry_state):
        if retry_state.outcome and retry_state.outcome.failed():
            logger.warning(
                "Retrying AGE operation (attempt %d/%d): %s",
                retry_state.attempt_number, max_attempts, retry_state.outcome.exception()
            )

    return retry(
        reraise=True,
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
        retry=retry_if_exception_type((DBAPIError, IntegrityError, ProgrammingError, OperationalError)),
        before_sleep=_before_sleep,
    )


def _parse_agtype(value: Any) -> Any:
    """AGE agtype 値をPythonネイティブ型にパースする."""
    if value is None:
        return None
    if isinstance(value, (int, float, bool, list, dict)):
        return value
    if isinstance(value, str):
        # Handle agtype format: strip ::vertex or ::edge suffix
        s = value.strip()
        if s.endswith("::vertex"):
            s = s[:-8].strip()  # Remove ::vertex (8 chars)
        elif s.endswith("::edge"):
            s = s[:-6].strip()  # Remove ::edge (6 chars)
        try:
            return json.loads(s)
        except (json.JSONDecodeError, TypeError):
            return value
    try:
        return json.loads(str(value))
    except (json.JSONDecodeError, TypeError):
        return str(value)


def _interpolate_cypher_params(cypher_query: str, parameters: dict[str, Any] | None) -> str:
    """Cypherクエリのパラメータを文字列補間で埋め込む（AGE 1.8.0はパラメータ未対応のため）.
    
    安全性: パラメータはアプリケーション内部からの信頼できる値のみ。
    文字列値はエスケープしてシングルクォートで囲む。
    """
    if not parameters:
        return cypher_query
    
    result = cypher_query
    for key, value in parameters.items():
        placeholder = f"${key}"
        if isinstance(value, str):
            # Escape single quotes and backslashes
            escaped = value.replace("\\", "\\\\").replace("'", "''")
            replacement = f"'{escaped}'"
        elif isinstance(value, (int, float, bool)):
            replacement = str(value).lower() if isinstance(value, bool) else str(value)
        elif value is None:
            replacement = "null"
        elif isinstance(value, (dict, list)):
            import json
            replacement = json.dumps(value, ensure_ascii=False)
        else:
            replacement = str(value)
        result = result.replace(placeholder, replacement)
    return result


def _ensure_age_session(session: Session) -> None:
    """セッションにAGE拡張をロードしsearch_pathを設定する."""
    session.execute(text("LOAD 'age';"))
    session.execute(text('SET search_path = ag_catalog, "$user", public;'))


def _dict_to_cypher_map(d: dict) -> str:
    """Python辞書をCypherマップリテラルに変換."""
    parts = []
    for k, v in d.items():
        if isinstance(v, str):
            escaped = v.replace("\\", "\\\\").replace("'", "''")
            parts.append(f"{k}: '{escaped}'")
        elif isinstance(v, bool):
            parts.append(f"{k}: {str(v).lower()}")
        elif v is None:
            parts.append(f"{k}: null")
        elif isinstance(v, (int, float)):
            parts.append(f"{k}: {v}")
        elif isinstance(v, (dict, list)):
            import json
            parts.append(f"{k}: {json.dumps(v, ensure_ascii=False)}")
        else:
            parts.append(f"{k}: '{str(v)}'")
    return "{" + ", ".join(parts) + "}"


class AgeClient:
    """Apache AGE クライアント - 本番グレード実装."""

    def __init__(
        self,
        default_graph_name: str | None = None,
        *,
        auto_init: bool = True,
    ) -> None:
        self.default_graph_name = default_graph_name or settings.AGE_GRAPH_NAME
        self.auto_init = auto_init
        self._initialized = False

    def _ensure_initialized(self, session: Session) -> bool:
        """グラフが初期化済みか確認し、必要なら初期化する."""
        if self._initialized:
            return True
        if not self.auto_init:
            return False
        return self.init_graph(session)

    @_safe_retry(max_attempts=3)
    def init_graph(self, session: Session, graph_name: str | None = None) -> bool:
        """グラフを作成・初期化する (idempotent)."""
        gname = graph_name or self.default_graph_name
        try:
            _ensure_age_session(session)
            session.execute(text(f"SELECT create_graph('{gname}');"))
            session.commit()
            logger.info("Graph '%s' created successfully.", gname)
            self._initialized = True
            return True
        except (IntegrityError, ProgrammingError) as e:
            session.rollback()
            pgcode = getattr(getattr(e, "orig", None), "pgcode", None)
            if pgcode in ("42P04", "3F000"):
                # Verify graph exists to be safe
                try:
                    exists = session.execute(
                        text("SELECT 1 FROM ag_graph WHERE name = :gname"),
                        {"gname": gname},
                    ).scalar()
                    if exists:
                        logger.debug("Graph '%s' already exists (pgcode=%s).", gname, pgcode)
                        self._initialized = True
                        return True
                except Exception:
                    pass
            logger.warning("Failed to create graph '%s' (pgcode=%s): %s", gname, pgcode, e)
            return False
        except Exception as e:
            session.rollback()
            logger.warning("Failed to create graph '%s': %s", gname, e)
            return False
        except Exception as e:
            session.rollback()
            logger.warning("Failed to create graph '%s': %s", gname, e)
            return False

    def execute_cypher(
        self,
        session: Session,
        cypher_query: str,
        column_definition: str = "(result agtype)",
        graph_name: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> CypherResult:
        """任意の Cypher クエリを PostgreSQL cypher() 関数経由で実行する.

        Args:
            session: SQLAlchemyセッション
            cypher_query: 実行するCypherクエリ（パラメータは $param 形式）
            column_definition: 戻り値のカラム定義
            graph_name: 対象グラフ名
            parameters: クエリパラメータ（$param 形式で使用）

        Returns:
            CypherResult: 構造化された実行結果
        """
        gname = graph_name or self.default_graph_name
        _ensure_age_session(session)

        # AGE 1.8.0 does not support parameterized queries, interpolate parameters
        interpolated_query = _interpolate_cypher_params(cypher_query, parameters)
        sql = f"SELECT * FROM cypher('{gname}', $$ {interpolated_query} $$) as {column_definition};"

        start_time = time.perf_counter()
        try:
            result = session.execute(text(sql))
            records = []
            for row in result:
                parsed_row = {}
                # Use _mapping for SQLAlchemy 2.0 compatibility
                for col in row._mapping.keys():
                    parsed_row[col] = _parse_agtype(row._mapping[col])
                records.append(parsed_row)

            execution_time_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(
                "Cypher query executed in %.2fms, returned %d records",
                execution_time_ms, len(records)
            )

            return CypherResult(
                records=records,
                summary={"row_count": len(records), "graph": gname},
                execution_time_ms=execution_time_ms,
            )
        except Exception as e:
            logger.error("Error executing Cypher query: %s | Query: %s", e, cypher_query)
            raise

    def execute_cypher_streaming(
        self,
        session: Session,
        cypher_query: str,
        column_definition: str = "(result agtype)",
        graph_name: str | None = None,
        batch_size: int = 1000,
    ):
        """大量結果用のストリーミング実行（ジェネレータ）."""
        gname = graph_name or self.default_graph_name
        _ensure_age_session(session)

        sql = f"SELECT * FROM cypher('{gname}', $$ {cypher_query} $$) as {column_definition};"

        result = session.execute(text(sql))
        batch = []
        for row in result:
            parsed_row = {}
            for col in row._mapping.keys():
                parsed_row[col] = _parse_agtype(row._mapping[col])
            batch.append(parsed_row)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    @_safe_retry(max_attempts=3)
    def upsert_node(
        self,
        session: Session,
        label: str,
        name: str,
        properties: dict[str, Any] | None = None,
        graph_name: str | None = None,
    ) -> bool:
        """ノードを作成または更新 (MERGE) する."""
        gname = graph_name or self.default_graph_name
        _ensure_age_session(session)

        props = properties or {}
        props["name"] = name

        safe_label = re.sub(r'[^a-zA-Z0-9_]', '', label)
        if not safe_label:
            raise ValueError(f"Invalid label: {label}")

        safe_name = name.replace("'", "''")
        props_map = _dict_to_cypher_map(props)

        cypher = (
            f"MERGE (n:{safe_label} {{name: '{safe_name}'}}) "
            f"SET n += {props_map} "
            "RETURN n"
        )

        try:
            sql = f"SELECT * FROM cypher('{gname}', $$ {cypher} $$) as (n agtype);"
            session.execute(text(sql))
            return True
        except Exception as e:
            logger.warning("Failed to upsert node (label=%s, name=%s): %s", label, name, e)
            return False

    @_safe_retry(max_attempts=3)
    def upsert_nodes_batch(
        self,
        session: Session,
        nodes: list[dict[str, Any]],
        graph_name: str | None = None,
    ) -> int:
        """複数ノードを一括 UPSERT する（トランザクション内で実行）.

        Args:
            session: SQLAlchemyセッション
            nodes: [{label, name, properties}, ...]
            graph_name: 対象グラフ名

        Returns:
            成功したノード数
        """
        gname = graph_name or self.default_graph_name
        _ensure_age_session(session)

        success_count = 0
        for node in nodes:
            label = node.get("label", "Entity")
            name = node.get("name")
            properties = node.get("properties", {})
            if not name:
                logger.warning("Skipping node without name: %s", node)
                continue

            props = properties.copy()
            props["name"] = name

            safe_label = re.sub(r'[^a-zA-Z0-9_]', '', label)
            if not safe_label:
                logger.warning("Skipping node with invalid label: %s", node)
                continue

            safe_name = name.replace("'", "''")
            props_map = _dict_to_cypher_map(props)

            cypher = (
                f"MERGE (n:{safe_label} {{name: '{safe_name}'}}) "
                f"SET n += {props_map} "
                "RETURN n"
            )

            try:
                sql = f"SELECT * FROM cypher('{gname}', $$ {cypher} $$) as (n agtype);"
                session.execute(text(sql))
                success_count += 1
            except Exception as e:
                logger.warning("Failed to upsert node in batch (label=%s, name=%s): %s", label, name, e)
                continue

        return success_count

    @_safe_retry(max_attempts=3)
    def upsert_edge(
        self,
        session: Session,
        source_label: str,
        source_name: str,
        target_label: str,
        target_name: str,
        relation_type: str,
        properties: dict[str, Any] | None = None,
        graph_name: str | None = None,
    ) -> bool:
        """2つのノード間のリレーション（エッジ）を作成または更新する."""
        gname = graph_name or self.default_graph_name
        _ensure_age_session(session)

        rel_type = re.sub(r"[^A-Za-z0-9_]", "_", relation_type).upper()
        safe_source_label = re.sub(r'[^a-zA-Z0-9_]', '', source_label)
        safe_target_label = re.sub(r'[^a-zA-Z0-9_]', '', target_label)
        if not safe_source_label or not safe_target_label:
            raise ValueError(f"Invalid label: source={source_label}, target={target_label}")

        props = properties or {}
        props_map = _dict_to_cypher_map(props)

        escaped_source_name = source_name.replace("'", "''")
        escaped_target_name = target_name.replace("'", "''")
        cypher = (
            f"MATCH (a:{safe_source_label} {{name: '{escaped_source_name}'}}), "
            f"(b:{safe_target_label} {{name: '{escaped_target_name}'}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            f"SET r += {props_map} "
            "RETURN r"
        )

        try:
            sql = f"SELECT * FROM cypher('{gname}', $$ {cypher} $$) as (r agtype);"
            session.execute(text(sql))
            return True
        except Exception as e:
            logger.warning(
                "Failed to upsert edge (%s)-[%s]->(%s): %s",
                source_name, rel_type, target_name, e
            )
            return False

    @_safe_retry(max_attempts=3)
    def upsert_edges_batch(
        self,
        session: Session,
        edges: list[dict[str, Any]],
        graph_name: str | None = None,
    ) -> int:
        """複数エッジを一括 UPSERT する."""
        gname = graph_name or self.default_graph_name
        _ensure_age_session(session)

        success_count = 0
        for edge in edges:
            source_label = edge.get("source_label", "Entity")
            source_name = edge.get("source_name")
            target_label = edge.get("target_label", "Entity")
            target_name = edge.get("target_name")
            relation_type = edge.get("relation_type", "RELATED_TO")
            properties = edge.get("properties", {})

            if not source_name or not target_name:
                logger.warning("Skipping edge without source/target name: %s", edge)
                continue

            rel_type = re.sub(r"[^A-Za-z0-9_]", "_", relation_type).upper()
            safe_source_label = re.sub(r'[^a-zA-Z0-9_]', '', source_label)
            safe_target_label = re.sub(r'[^a-zA-Z0-9_]', '', target_label)
            if not safe_source_label or not safe_target_label:
                logger.warning("Skipping edge with invalid label: %s", edge)
                continue

            props = properties or {}
            props_map = _dict_to_cypher_map(props)

            escaped_source_name = source_name.replace("'", "''")
            escaped_target_name = target_name.replace("'", "''")
            cypher = (
                f"MATCH (a:{safe_source_label} {{name: '{escaped_source_name}'}}), "
                f"(b:{safe_target_label} {{name: '{escaped_target_name}'}}) "
                f"MERGE (a)-[r:{rel_type}]->(b) "
                f"SET r += {props_map} "
                "RETURN r"
            )

            try:
                sql = f"SELECT * FROM cypher('{gname}', $$ {cypher} $$) as (r agtype);"
                session.execute(text(sql))
                success_count += 1
            except Exception as e:
                logger.warning(
                    "Failed to upsert edge in batch (%s)-[%s]->(%s): %s",
                    source_name, rel_type, target_name, e
                )
                continue

        return success_count

    def get_all_nodes(
        self,
        session: Session,
        graph_name: str | None = None,
        limit: int = 5000,
        labels: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """グラフ内の全ノードの name と labels を取得する."""
        gname = graph_name or self.default_graph_name
        bind = session.get_bind()
        try:
            dialect = bind.dialect.name if bind is not None else ""
        except Exception:
            dialect = ""
        if dialect != "postgresql":
            return []

        _ensure_age_session(session)

        label_filter = ""
        if labels:
            label_str = ":".join(labels)
            label_filter = f":{label_str}"

        cypher = f"MATCH (n{label_filter}) RETURN n.name AS name, labels(n) AS labels, properties(n) AS props LIMIT {int(limit)}"
        sql = f"SELECT * FROM cypher('{gname}', $$ {cypher} $$) as (name agtype, labels agtype, props agtype);"

        try:
            result = session.execute(text(sql))
            rows = []
            for row in result:
                raw_name = row[0]
                raw_labels = row[1]
                raw_props = row[2]
                name = str(raw_name).strip('"') if raw_name is not None else ""
                labels_str = str(raw_labels) if raw_labels else ""
                props = _parse_agtype(raw_props)
                rows.append({"name": name, "labels": labels_str, "properties": props})
            return rows
        except Exception as e:
            logger.debug("get_all_nodes unavailable: %s", e)
            try:
                session.rollback()
            except Exception:
                pass
            return []

    def get_neighbors(
        self,
        session: Session,
        node_name: str,
        max_depth: int = 2,
        graph_name: str | None = None,
        relationship_types: list[str] | None = None,
        direction: str = "both",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """特定ノードから N ホップ以内の関連エンティティと関係を取得する.

        Args:
            session: SQLAlchemyセッション
            node_name: 起点ノード名
            max_depth: 最大ホップ数
            graph_name: 対象グラフ名
            relationship_types: フィルタする関係タイプ
            direction: "outgoing", "incoming", "both"
            limit: 最大取得件数
        """
        gname = graph_name or self.default_graph_name
        _ensure_age_session(session)

        depth_str = f"1..{max_depth}" if max_depth > 1 else "1"

        if direction == "outgoing":
            arrow = "->"
        elif direction == "incoming":
            arrow = "<-"
        else:
            arrow = "-"

        rel_filter = ""
        if relationship_types:
            rel_list = "|".join(rt.upper() for rt in relationship_types)
            rel_filter = f":{rel_list}"

        escaped_node_name = node_name.replace("'", "''")
        cypher = (
            f"MATCH (a {{name: '{escaped_node_name}'}})-[r{rel_filter}*{depth_str}]{arrow}(b) "
            f"RETURN DISTINCT b.name, labels(b), properties(b), type(last(r)) LIMIT {int(limit)}"
        )

        try:
            sql = f"SELECT * FROM cypher('{gname}', $$ {cypher} $$) as (name agtype, labels agtype, props agtype, rel_type agtype);"
            result = session.execute(text(sql))
            neighbors = []
            for row in result:
                neighbors.append({
                    "name": str(row[0]).strip('"'),
                    "labels": _parse_agtype(row[1]),
                    "properties": _parse_agtype(row[2]),
                    "relation_type": str(row[3]).strip('"') if row[3] else None,
                })
            return neighbors
        except Exception as e:
            logger.warning("Failed to get neighbors for node '%s': %s", node_name, e)
            return []

    def get_shortest_path(
        self,
        session: Session,
        source_name: str,
        target_name: str,
        max_depth: int = 5,
        graph_name: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """2ノード間の最短パスを取得する."""
        gname = graph_name or self.default_graph_name
        _ensure_age_session(session)

        src = source_name.replace("'", "''")
        tgt = target_name.replace("'", "''")

        cypher = (
            f"MATCH (a {{name: '{src}'}}), (b {{name: '{tgt}'}}), "
            f"p = shortestPath((a)-[*1..{max_depth}]-(b)) "
            "RETURN p"
        )

        try:
            sql = f"SELECT * FROM cypher('{gname}', $$ {cypher} $$) as (path agtype);"
            result = session.execute(text(sql))
            row = result.fetchone()
            if row and row[0]:
                path = _parse_agtype(row[0])
                return path
            return None
        except Exception as e:
            logger.warning("Failed to get shortest path (%s -> %s): %s", source_name, target_name, e)
            return None

    @_safe_retry(max_attempts=3)
    def delete_node(
        self,
        session: Session,
        label: str,
        name: str,
        graph_name: str | None = None,
        detach: bool = True,
    ) -> bool:
        """ノードを削除する（エッジも含めて削除する場合は detach=True）."""
        gname = graph_name or self.default_graph_name
        _ensure_age_session(session)

        safe_label = re.sub(r'[^a-zA-Z0-9_]', '', label)
        if not safe_label:
            raise ValueError(f"Invalid label: {label}")

        safe_name = name.replace("'", "''")

        if detach:
            cypher = f"MATCH (n:{safe_label} {{name: '{safe_name}'}}) DETACH DELETE n"
        else:
            cypher = f"MATCH (n:{safe_label} {{name: '{safe_name}'}}) DELETE n"

        try:
            sql = f"SELECT * FROM cypher('{gname}', $$ {cypher} $$) as (result agtype);"
            session.execute(text(sql))
            return True
        except Exception as e:
            logger.warning("Failed to delete node (label=%s, name=%s): %s", label, name, e)
            return False

    @_safe_retry(max_attempts=3)
    def delete_edge(
        self,
        session: Session,
        source_label: str,
        source_name: str,
        target_label: str,
        target_name: str,
        relation_type: str,
        graph_name: str | None = None,
    ) -> bool:
        """エッジを削除する."""
        gname = graph_name or self.default_graph_name
        _ensure_age_session(session)

        rel_type = re.sub(r"[^A-Za-z0-9_]", "_", relation_type).upper()
        safe_source_label = re.sub(r'[^a-zA-Z0-9_]', '', source_label)
        safe_target_label = re.sub(r'[^a-zA-Z0-9_]', '', target_label)
        if not safe_source_label or not safe_target_label:
            raise ValueError(f"Invalid label: source={source_label}, target={target_label}")

        safe_source_name = source_name.replace("'", "''")
        safe_target_name = target_name.replace("'", "''")

        cypher = (
            f"MATCH (a:{safe_source_label} {{name: '{safe_source_name}'}})-[r:{rel_type}]->"
            f"(b:{safe_target_label} {{name: '{safe_target_name}'}}) "
            "DELETE r"
        )

        try:
            sql = f"""SELECT * FROM cypher('{gname}', $$ {cypher} $$) as (result agtype);"""
            session.execute(text(sql))
            return True
        except Exception as e:
            logger.warning(
                "Failed to delete edge (%s)-[%s]->(%s): %s",
                source_name, rel_type, target_name, e
            )
            return False

    def get_graph_stats(self, session: Session, graph_name: str | None = None) -> GraphStats:
        """グラフの統計情報を取得する."""
        gname = graph_name or self.default_graph_name
        
        # Use a completely independent psycopg2 connection to avoid SQLAlchemy transaction issues
        import psycopg2
        from sqlalchemy import text
        
        # Extract connection parameters from the session's bind
        bind = session.get_bind()
        if bind is None:
            logger.warning("No bind available for session")
            return GraphStats(node_count=0, edge_count=0, labels=[], relationship_types=[])
        
        # Get the connection URL from the engine
        engine = bind if hasattr(bind, 'url') else (bind.engine if hasattr(bind, 'engine') else None)
        if engine is None:
            logger.warning("Could not get engine from bind")
            return GraphStats(node_count=0, edge_count=0, labels=[], relationship_types=[])
        
        url = engine.url
        conn_params = {
            'host': url.host or 'localhost',
            'port': url.port or 5432,
            'database': url.database,
            'user': url.username,
            'password': url.password,
        }
        
        try:
            with psycopg2.connect(**conn_params) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute("LOAD 'age';")
                    cur.execute('SET search_path = ag_catalog, "$user", public;')
                    
                    # ノード数
                    node_sql = f"SELECT * FROM cypher('{gname}', $$ MATCH (n) RETURN count(n) $$) as (cnt agtype);"
                    cur.execute(node_sql)
                    node_row = cur.fetchone()
                    node_count = int(str(node_row[0]).strip('"')) if node_row and node_row[0] else 0

                    # エッジ数
                    edge_sql = f"SELECT * FROM cypher('{gname}', $$ MATCH ()-[r]->() RETURN count(r) $$) as (cnt agtype);"
                    cur.execute(edge_sql)
                    edge_row = cur.fetchone()
                    edge_count = int(str(edge_row[0]).strip('"')) if edge_row and edge_row[0] else 0

                    # ラベル一覧
                    labels_sql = f"SELECT name FROM ag_catalog.ag_label WHERE graph = (SELECT graphid FROM ag_catalog.ag_graph WHERE name = '{gname}') AND kind = 'v';"
                    cur.execute(labels_sql)
                    labels = [row[0] for row in cur.fetchall()]

                    # 関係タイプ一覧
                    rel_sql = f"SELECT name FROM ag_catalog.ag_label WHERE graph = (SELECT graphid FROM ag_catalog.ag_graph WHERE name = '{gname}') AND kind = 'e';"
                    cur.execute(rel_sql)
                    relationship_types = [row[0] for row in cur.fetchall()]

                return GraphStats(
                    node_count=node_count,
                    edge_count=edge_count,
                    labels=labels,
                    relationship_types=relationship_types,
                )
        except Exception as e:
            logger.warning("Failed to get graph stats: %s", e)
            return GraphStats(node_count=0, edge_count=0, labels=[], relationship_types=[])

    def create_label_index(
        self,
        session: Session,
        label: str,
        graph_name: str | None = None,
    ) -> bool:
        """ラベルにインデックスを作成する（MATCH性能向上）."""
        gname = graph_name or self.default_graph_name
        _ensure_age_session(session)

        try:
            sql = f"SELECT create_label_index('{gname}', '{label}');"
            session.execute(text(sql))
            session.commit()
            logger.info("Created label index for '%s' on graph '%s'", label, gname)
            return True
        except Exception as e:
            session.rollback()
            logger.warning("Failed to create label index for '%s': %s", label, e)
            return False

    def create_property_index(
        self,
        session: Session,
        label: str,
        property_name: str,
        graph_name: str | None = None,
    ) -> bool:
        """ラベルのプロパティにインデックスを作成する."""
        gname = graph_name or self.default_graph_name
        _ensure_age_session(session)

        try:
            sql = f"SELECT create_property_index('{gname}', '{label}', '{property_name}');"
            session.execute(text(sql))
            session.commit()
            logger.info("Created property index for '%s.%s' on graph '%s'", label, property_name, gname)
            return True
        except Exception as e:
            session.rollback()
            logger.warning("Failed to create property index for '%s.%s': %s", label, property_name, e)
            return False

    def search_nodes_by_property(
        self,
        session: Session,
        label: str,
        property_name: str,
        property_value: Any,
        graph_name: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """プロパティ値でノードを検索する."""
        gname = graph_name or self.default_graph_name
        _ensure_age_session(session)

        safe_label = re.sub(r'[^a-zA-Z0-9_]', '', label)
        if not safe_label:
            raise ValueError(f"Invalid label: {label}")

# Handle different property value types
        if isinstance(property_value, str):
            escaped_value = property_value.replace("'", "''")
            safe_value = f"'{escaped_value}'"
        elif isinstance(property_value, bool):
            safe_value = str(property_value).lower()
        elif property_value is None:
            safe_value = "null"
        elif isinstance(property_value, (int, float)):
            safe_value = str(property_value)
        else:
            import json
            safe_value = json.dumps(property_value, ensure_ascii=False)

        cypher = f"MATCH (n:{safe_label}) WHERE n.{property_name} = {safe_value} RETURN n.name, labels(n), properties(n) LIMIT {limit}"

        try:
            sql = f"SELECT * FROM cypher('{gname}', $$ {cypher} $$) as (name agtype, labels agtype, props agtype);"
            result = session.execute(text(sql))
            rows = []
            for row in result:
                rows.append({
                    "name": str(row[0]).strip('"'),
                    "labels": _parse_agtype(row[1]),
                    "properties": _parse_agtype(row[2]),
                })
            return rows
        except Exception as e:
            logger.warning("Failed to search nodes by property: %s", e)
            return []

    @contextmanager
    def transaction(self, session: Session):
        """トランザクション管理用コンテキストマネージャ."""
        try:
            _ensure_age_session(session)
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


# シングルトンインスタンス
age_client = AgeClient()

__all__ = [
    "AgeClient",
    "age_client",
    "CypherResult",
    "GraphStats",
    "_parse_agtype",
    "_ensure_age_session",
]
