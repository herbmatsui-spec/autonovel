"""GraphStore インターフェース実装 (Week 2 Step 11)。

キャラクター間の感情エッジをグラフデータベース (Kuzu) に永続化する。
Kuzu が利用不可能な環境向けにインメモリ実装も提供する。
"""
from __future__ import annotations

import abc
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GraphStore(abc.ABC):
    """感情グラフストアの抽象基底クラス。

    スキーマ:
        ノード: Character(name)
        エッジ: FEELS_TOWARD{affection, tension, fear, trust, intimacy, cause, episode, timestamp}
    """

    @abc.abstractmethod
    def upsert_edge(self, source: str, target: str, props: Dict[str, Any]) -> None:
        """感情エッジを追加・更新する。"""
        ...

    @abc.abstractmethod
    def get_latest_edge(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        """指定ペアの最新エッジを取得する。"""
        ...

    @abc.abstractmethod
    def query_causal_path(self, source: str, target: str, max_hops: int = 3) -> List[Dict[str, Any]]:
        """因果パス (source から target への感情エッジ列) を取得する。"""
        ...

    @abc.abstractmethod
    def delete_edge(self, source: str, target: str, beat_id: str = None) -> bool:
        """エッジ削除（beat_id指定時は該当のみ削除）"""
        ...


class InMemoryGraphStore(GraphStore):
    """インメモリ実装のグラフストア (テスト・フォールバック用)。"""

    def __init__(self) -> None:
        # (source, target) → [props, ...] (時系列順)
        self._edges: Dict[tuple[str, str], List[Dict[str, Any]]] = {}

    def upsert_edge(self, source: str, target: str, props: Dict[str, Any]) -> None:
        data = dict(props or {})
        data.setdefault("timestamp", time.time())
        self._edges.setdefault((source, target), []).append(data)

    def get_latest_edge(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        history = self._edges.get((source, target))
        if not history:
            return None
        return dict(history[-1])

    def query_causal_path(self, source: str, target: str, max_hops: int = 3) -> List[Dict[str, Any]]:
        """BFS で source → target のパスを探索する。

        Returns:
            パス上のエッジ情報のリスト:
            [{"from": ..., "to": ..., "cause": ..., "episode": ...}, ...]
            パスが存在しない場合は空リスト。
        """
        if source == target:
            return []

        # BFS
        from collections import deque

        queue: deque[tuple[str, List[Dict[str, Any]]]] = deque([(source, [])])
        visited = {source}

        while queue:
            current, path = queue.popleft()
            if len(path) >= max_hops:
                continue
            for (s, t), history in self._edges.items():
                if s != current:
                    continue
                if t in visited:
                    continue
                latest = dict(history[-1])
                new_path = path + [{
                    "from": s,
                    "to": t,
                    "cause": latest.get("cause", ""),
                    "episode": latest.get("episode"),
                    "emotions": {
                        k: latest.get(k)
                        for k in ("affection", "tension", "fear", "trust", "intimacy")
                        if k in latest
                    },
                }]
                if t == target:
                    return new_path
                visited.add(t)
                queue.append((t, new_path))
        return []

    def get_all_edges(self) -> Dict[tuple[str, str], List[Dict[str, Any]]]:
        """全エッジを取得 (デバッグ用)。"""
        return {k: list(v) for k, v in self._edges.items()}

    def delete_edge(self, source: str, target: str, beat_id: str = None) -> bool:
        """エッジ削除（beat_id指定時は該当のみ削除、未指定なら全削除）"""
        key = (source, target)
        if key not in self._edges:
            return False
        
        if beat_id is None:
            # 全削除
            del self._edges[key]
            return True
        
        # beat_idでフィルタ
        original_len = len(self._edges[key])
        self._edges[key] = [e for e in self._edges[key] if e.get("beat_id") != beat_id]
        if len(self._edges[key]) == 0:
            del self._edges[key]
        return len(self._edges.get(key, [])) < original_len


class KuzuGraphStore(GraphStore):
    """Kuzu 実装のグラフストア。

    Args:
        db_path: Kuzu データベースファイルパス (":memory:" でインメモリ)
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._connection: Any = None
        self._available = False
        try:
            import kuzu  # type: ignore[import-not-found]

            self._db = kuzu.Database(db_path)
            self._connection = kuzu.Connection(self._db)
            self._init_schema()
            self._available = True
        except ImportError:
            logger.warning("kuzu not installed; KuzuGraphStore is not functional")
        except Exception as e:  # pragma: no cover - Kuzu 起動失敗
            logger.warning("Kuzu initialization failed: %s", e)

    def _init_schema(self) -> None:
        """ノード・エッジテーブルを作成する。"""
        self._connection.execute("CREATE NODE TABLE IF NOT EXISTS Character (name STRING, PRIMARY KEY (name))")
        self._connection.execute(
            "CREATE EDGE TABLE IF NOT EXISTS FEELS_TOWARD "
            "(FROM Character TO Character, "
            "affection DOUBLE, tension DOUBLE, fear DOUBLE, trust DOUBLE, intimacy DOUBLE, "
            "cause STRING, episode INT64, timestamp DOUBLE)"
        )

    def _ensure_node(self, name: str) -> None:
        """キャラクターノードを作成 (既存なら MERGE 的に無視)。"""
        self._connection.execute(f"MERGE (c:Character {{name: '{self._escape(name)}'}})")

    @staticmethod
    def _escape(value: Any) -> str:
        """文字列のエスケープ (単一引用符)。"""
        return str(value).replace("\\", "\\\\").replace("'", "\\'")

    def upsert_edge(self, source: str, target: str, props: Dict[str, Any]) -> None:
        if not self._available:
            logger.debug("KuzuGraphStore unavailable; skipping upsert_edge")
            return
        data = dict(props or {})
        data.setdefault("timestamp", time.time())
        self._ensure_node(source)
        self._ensure_node(target)
        params = {
            "src": str(source),
            "dst": str(target),
            "affection": float(data.get("affection", 0.0)),
            "tension": float(data.get("tension", 0.0)),
            "fear": float(data.get("fear", 0.0)),
            "trust": float(data.get("trust", 0.0)),
            "intimacy": float(data.get("intimacy", 0.0)),
            "cause": str(data.get("cause", "")),
            "episode": int(data.get("episode", 0)),
            "timestamp": float(data.get("timestamp", 0.0)),
        }
        self._connection.execute(
            "MATCH (a:Character {name: $src}), (b:Character {name: $dst}) "
            "CREATE (a)-[:FEELS_TOWARD {"
            "affection: $affection, tension: $tension, fear: $fear, trust: $trust, "
            "intimacy: $intimacy, cause: $cause, episode: $episode, timestamp: $timestamp}]->(b)",
            params,
        )

    def get_latest_edge(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        if not self._available:
            return None
        result = self._connection.execute(
            "MATCH (a:Character {name: $src})-[e:FEELS_TOWARD]->(b:Character {name: $dst}) "
            "RETURN e.affection, e.tension, e.fear, e.trust, e.intimacy, e.cause, e.episode, e.timestamp "
            "ORDER BY e.timestamp DESC LIMIT 1",
            {"src": str(source), "dst": str(target)},
        )
        rows = result.get_next() if result.has_next() else None
        if rows is None:
            return None
        return {
            "affection": rows[0],
            "tension": rows[1],
            "fear": rows[2],
            "trust": rows[3],
            "intimacy": rows[4],
            "cause": rows[5],
            "episode": rows[6],
            "timestamp": rows[7],
        }

    def query_causal_path(self, source: str, target: str, max_hops: int = 3) -> List[Dict[str, Any]]:
        if not self._available:
            return []
        result = self._connection.execute(
            "MATCH (a:Character {name: $src})-[e:FEELS_TOWARD*1..$hops]->(b:Character {name: $dst}) "
            "RETURN [x IN e | x.cause] AS causes, [x IN e | x.episode] AS episodes LIMIT 1",
            {"src": str(source), "dst": str(target), "hops": int(max_hops)},
        )
        if not result.has_next():
            return []
        causes, episodes = result.get_next()
        path: List[Dict[str, Any]] = []
        prev = str(source)
        for i, cause in enumerate(causes or []):
            node = str(target) if i == len(causes) - 1 else ""
            path.append({
                "from": prev,
                "to": node,
                "cause": cause,
                "episode": episodes[i] if i < len(episodes) else None,
            })
        return path

    def delete_edge(self, source: str, target: str, beat_id: str = None) -> bool:
        """エッジ削除（beat_id指定時は該当のみ削除）"""
        if not self._available:
            return False
        try:
            if beat_id is None:
                # 全削除
                self._connection.execute(
                    "MATCH (a:Character {name: $src})-[e:FEELS_TOWARD]->(b:Character {name: $dst}) DELETE e",
                    {"src": str(source), "dst": str(target)},
                )
            else:
                # beat_idでフィルタして削除
                self._connection.execute(
                    "MATCH (a:Character {name: $src})-[e:FEELS_TOWARD {beat_id: $beat_id}]->(b:Character {name: $dst}) DELETE e",
                    {"src": str(source), "dst": str(target), "beat_id": beat_id},
                )
            return True
        except Exception as e:
            logger.warning("Failed to delete edge: %s", e)
            return False


__all__ = ["GraphStore", "InMemoryGraphStore", "KuzuGraphStore"]
