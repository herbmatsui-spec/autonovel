"""Apache AGE (openCypher) 連携クライアントモジュール.

PostgreSQL の Apache AGE 拡張を利用して、グラフの初期化、ノード・エッジの作成、
および近傍探索（Graph Traversal）を SQL 経由で透過的に実行する。
"""
from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.backend.config import settings
from src.backend.logging_config import get_logger

logger = get_logger("age_client")


class AgeClient:
    """Apache AGE クライアント."""

    def __init__(self, default_graph_name: str | None = None) -> None:
        self.default_graph_name = default_graph_name or settings.AGE_GRAPH_NAME

    def init_graph(self, session: Session, graph_name: str | None = None) -> bool:
        """グラフを作成・初期化する."""
        gname = graph_name or self.default_graph_name
        try:
            # AGE 拡張をロード
            session.execute(text("LOAD 'age';"))
            session.execute(text('SET search_path = ag_catalog, "$user", public;'))
            session.execute(text(f"SELECT create_graph('{gname}');"))
            session.commit()
            logger.info("Graph '%s' created successfully.", gname)
            return True
        except Exception as e:
            session.rollback()
            # すでに存在している場合は正常
            if "already exists" in str(e).lower():
                logger.debug("Graph '%s' already exists.", gname)
                return True
            logger.warning("Failed to create graph '%s': %s", gname, e)
            return False

    def execute_cypher(
        self,
        session: Session,
        cypher_query: str,
        column_definition: str = "(result agtype)",
        graph_name: str | None = None,
    ) -> list[Any]:
        """任意の Cypher クエリを PostgreSQL cypher() 関数経由で実行する."""
        gname = graph_name or self.default_graph_name
        sql = f"SELECT * FROM cypher('{gname}', $$ {cypher_query} $$) as {column_definition};"

        try:
            result = session.execute(text(sql))
            return [row for row in result]
        except Exception as e:
            logger.error("Error executing Cypher query: %s | Query: %s", e, cypher_query)
            raise

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
        props = properties or {}
        props["name"] = name

        # 安全なプロパティ文字列を構築
        props_json = json.dumps(props, ensure_ascii=False)
        # AGE のプロパティ指定形式に変換
        cypher = f"MERGE (n:{label} {{name: '{name}'}}) SET n += {props_json} RETURN n"

        try:
            sql = f"SELECT * FROM cypher('{gname}', $$ {cypher} $$) as (n agtype);"
            session.execute(text(sql))
            return True
        except Exception as e:
            logger.warning("Failed to upsert node (label=%s, name=%s): %s", label, name, e)
            return False

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
        rel_type = re.sub(r"[^A-Za-z0-9_]", "_", relation_type).upper()
        props_json = json.dumps(properties or {}, ensure_ascii=False)

        cypher = (
            f"MATCH (a:{source_label} {{name: '{source_name}'}}), (b:{target_label} {{name: '{target_name}'}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) "
            f"SET r += {props_json} "
            f"RETURN r"
        )

        try:
            sql = f"SELECT * FROM cypher('{gname}', $$ {cypher} $$) as (r agtype);"
            session.execute(text(sql))
            return True
        except Exception as e:
            logger.warning(
                "Failed to upsert edge (%s)-[%s]->(%s): %s",
                source_name,
                rel_type,
                target_name,
                e,
            )
            return False

    def get_neighbors(
        self,
        session: Session,
        node_name: str,
        max_depth: int = 2,
        graph_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """特定ノードから N ホップ以内の関連エンティティと関係を取得する."""
        gname = graph_name or self.default_graph_name
        depth_str = f"1..{max_depth}" if max_depth > 1 else "1"

        cypher = (
            f"MATCH (a {{name: '{node_name}'}})-[r*{depth_str}]-(b) "
            f"RETURN DISTINCT b.name, labels(b), b, type(last(r)) LIMIT 30"
        )

        try:
            sql = f"SELECT * FROM cypher('{gname}', $$ {cypher} $$) as (name agtype, labels agtype, props agtype, rel_type agtype);"
            result = session.execute(text(sql))
            neighbors = []
            for row in result:
                neighbors.append({
                    "name": str(row[0]).strip('"'),
                    "labels": row[1],
                    "properties": row[2],
                    "relation_type": str(row[3]).strip('"') if row[3] else None,
                })
            return neighbors
        except Exception as e:
            logger.warning("Failed to get neighbors for node '%s': %s", node_name, e)
            return []


# シングルトンインスタンス
age_client = AgeClient()

__all__ = ["AgeClient", "age_client"]
