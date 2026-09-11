"""Cypher クエリを NetworkX 操作に変換するトランスレーター.

既存の `MATCH (c:Character)-[:FRIEND]->(t)` 形式のクエリを、
NetworkX のノード・エッジ走査コードに透過的に変換する。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedPattern:
    """パース済みパターン."""
    node_patterns: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    where_clauses: list[str]
    return_clause: str | None = None
    limit: int | None = None


class CypherToNetworkXTranslator:
    """Cypher 風クエリを NetworkX 操作に変換するトランスレーター.

    サポートする Cypher 機能:
    - MATCH (node:Label {property: value})
    - 単純なリレーション: (a)-[:REL]->(b)
    - 可変長パス: (a)-[:REL*1..2]->(b)
    - WHERE 句 (簡易)
    - RETURN 句
    - LIMIT 句
    """

    NODE_PATTERN = re.compile(
        r"\((\w+)?(?::(\w+))?(?:\s*\{([^}]+)\})?\)"
    )
    REL_PATTERN = re.compile(
        r"\[(\w+)?(?::(\w+))?(?:\*(\d+)(?:\.\.(\d+))?)?(?:\s*\{([^}]+)\})?\]"
    )
    ARROW_PATTERN = re.compile(r"(-\[.*?\]-|<-\[.*?\]-|-\[.*?\]->)")

    def __init__(self) -> None:
        self._store = None

    def set_store(self, store: Any) -> None:
        """NetworkXGraphStore インスタンスを設定する."""
        self._store = store

    def translate(self, cypher: str) -> ParsedPattern:
        """Cypher クエリをパースして NetworkX 操作可能な形式に変換する.

        Args:
            cypher: Cypher クエリ文字列

        Returns:
            ParsedPattern: パース済みパターン
        """
        cypher = cypher.strip()
        if not cypher.upper().startswith("MATCH"):
            raise ValueError("Only MATCH queries are supported")

        parsed = ParsedPattern(node_patterns=[], relationships=[], where_clauses=[])

        match_section = self._extract_match_section(cypher)
        where_section = self._extract_where_section(cypher)
        return_section = self._extract_return_section(cypher)
        limit_section = self._extract_limit_section(cypher)

        parsed.return_clause = return_section
        parsed.limit = limit_section
        parsed.where_clauses = where_section

        if match_section:
            self._parse_match_patterns(match_section, parsed)

        return parsed

    def execute(self, cypher: str) -> list[dict[str, Any]]:
        """Cypher クエリを実行して結果を返す.

        Args:
            cypher: Cypher クエリ文字列

        Returns:
            実行結果のリスト
        """
        if self._store is None:
            raise RuntimeError("Store not set. Call set_store() first.")

        parsed = self.translate(cypher)
        return self._execute_parsed(parsed)

    def _execute_parsed(self, parsed: ParsedPattern) -> list[dict[str, Any]]:
        """パース済みパターンを実行する."""
        if not parsed.node_patterns:
            return []

        start_node = parsed.node_patterns[0]
        node_name = start_node.get("name")
        if not node_name:
            return []

        hops = 2
        if parsed.relationships:
            rel = parsed.relationships[0]
            if rel.get("max_hops"):
                hops = rel["max_hops"]

        rel_types = [r.get("type") for r in parsed.relationships if r.get("type")]
        direction = "both"
        if parsed.relationships:
            arrow = parsed.relationships[0].get("direction", "both")
            if arrow == ">":
                direction = "outgoing"
            elif arrow == "<":
                direction = "incoming"

        result = self._store.find_neighbors(
            entity_id=node_name,
            hops=hops,
            relationship_types=rel_types if rel_types else None,
            direction=direction,
            limit=parsed.limit or 50,
        )

        output = []
        for node in result.nodes:
            output.append({
                "name": node.name,
                "label": node.label,
                "properties": node.properties,
            })
        return output

    def _extract_match_section(self, cypher: str) -> str:
        """MATCH 句を抽出する."""
        match = re.search(r"MATCH\s+(.*?)(?:\s+WHERE|\s+RETURN|\s+LIMIT|$)", cypher, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else ""

    def _extract_where_section(self, cypher: str) -> list[str]:
        """WHERE 句を抽出する."""
        match = re.search(r"WHERE\s+(.*?)(?:\s+RETURN|\s+LIMIT|$)", cypher, re.IGNORECASE | re.DOTALL)
        if not match:
            return []
        where_str = match.group(1).strip()
        return [c.strip() for c in where_str.split("AND")]

    def _extract_return_section(self, cypher: str) -> str | None:
        """RETURN 句を抽出する."""
        match = re.search(r"RETURN\s+(.*?)(?:\s+LIMIT|$)", cypher, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else None

    def _extract_limit_section(self, cypher: str) -> int | None:
        """LIMIT 句を抽出する."""
        match = re.search(r"LIMIT\s+(\d+)", cypher, re.IGNORECASE)
        return int(match.group(1)) if match else None

    def _parse_match_patterns(self, match_section: str, parsed: ParsedPattern) -> None:
        """MATCH パターンをパースする."""
        current_node = None
        tokens = self._tokenize_match(match_section)

        for token in tokens:
            if token["type"] == "node":
                node_info = {
                    "var": token["var"],
                    "label": token["label"],
                    "properties": token["properties"],
                }
                if token.get("name_prop"):
                    node_info["name"] = token["name_prop"]
                parsed.node_patterns.append(node_info)
                current_node = token["var"]

            elif token["type"] == "relationship":
                rel_info = {
                    "var": token["var"],
                    "type": token["rel_type"],
                    "min_hops": token["min_hops"],
                    "max_hops": token["max_hops"],
                    "properties": token["properties"],
                    "direction": token["direction"],
                    "source_var": current_node,
                }
                parsed.relationships.append(rel_info)

    def _tokenize_match(self, match_section: str) -> list[dict[str, Any]]:
        """MATCH 句をトークン化する."""
        tokens = []
        pos = 0
        match_section = match_section.replace("\n", " ").replace("\r", "")

        while pos < len(match_section):
            if match_section[pos].isspace() or match_section[pos] == ",":
                pos += 1
                continue

            if match_section[pos] == "(":
                end_pos = match_section.find(")", pos)
                if end_pos == -1:
                    break
                node_str = match_section[pos:end_pos + 1]
                node_token = self._parse_node(node_str)
                tokens.append(node_token)
                pos = end_pos + 1
                continue

            if match_section[pos] == "[":
                end_pos = match_section.find("]", pos)
                if end_pos == -1:
                    break
                rel_str = match_section[pos:end_pos + 1]
                rel_token = self._parse_relationship(rel_str)
                tokens.append(rel_token)
                pos = end_pos + 1
                continue

            if match_section[pos:pos+2] in ("->", "<-", "-"):
                pos += 2 if match_section[pos+1] in (">", "<") else 1
                continue

            pos += 1

        return tokens

    def _parse_node(self, node_str: str) -> dict[str, Any]:
        """ノードパターンをパースする."""
        match = self.NODE_PATTERN.match(node_str)
        if not match:
            return {"type": "node", "var": "", "label": None, "properties": {}, "name_prop": None}

        var, label, props_str = match.groups()
        properties = {}
        name_prop = None

        if props_str:
            for prop in props_str.split(","):
                prop = prop.strip()
                if ":" in prop:
                    key, val = prop.split(":", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    properties[key] = val
                    if key == "name":
                        name_prop = val

        return {
            "type": "node",
            "var": var or "",
            "label": label,
            "properties": properties,
            "name_prop": name_prop,
        }

    def _parse_relationship(self, rel_str: str) -> dict[str, Any]:
        """リレーションパターンをパースする."""
        match = self.REL_PATTERN.match(rel_str)
        if not match:
            return {
                "type": "relationship",
                "var": "",
                "rel_type": None,
                "min_hops": 1,
                "max_hops": 1,
                "properties": {},
                "direction": "both",
            }

        var, rel_type, min_hops, max_hops, props_str = match.groups()

        direction = "both"
        if rel_str.startswith("-["):
            direction = "outgoing"
        elif rel_str.startswith("<-["):
            direction = "incoming"

        min_h = int(min_hops) if min_hops else 1
        max_h = int(max_hops) if max_hops else min_h

        properties = {}
        if props_str:
            for prop in props_str.split(","):
                prop = prop.strip()
                if ":" in prop:
                    key, val = prop.split(":", 1)
                    properties[key.strip()] = val.strip().strip("'\"")

        return {
            "type": "relationship",
            "var": var or "",
            "rel_type": rel_type,
            "min_hops": min_h,
            "max_hops": max_h,
            "properties": properties,
            "direction": direction,
        }


def translate_cypher_to_networkx(cypher: str, store: Any) -> list[dict[str, Any]]:
    """Cypher クエリを NetworkX 操作に変換して実行する便利関数.

    Args:
        cypher: Cypher クエリ文字列
        store: NetworkXGraphStore インスタンス

    Returns:
        実行結果のリスト
    """
    translator = CypherToNetworkXTranslator()
    translator.set_store(store)
    return translator.execute(cypher)