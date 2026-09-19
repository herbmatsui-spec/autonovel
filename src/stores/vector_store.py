"""Vector store interface and Redis implementation for emotional vectors."""
from __future__ import annotations

import abc
import json
import logging
from typing import Any, Optional

import redis

from src.pipeline.emotional_residue import EmotionalVector

logger = logging.getLogger(__name__)


class VectorStore(abc.ABC):
    """感情ベクトルストアの抽象基底クラス"""

    @abc.abstractmethod
    def upsert(self, namespace: str, key: str, vector: EmotionalVector) -> None:
        """ベクトルを追加・更新"""
        ...

    @abc.abstractmethod
    def get_latest(self, namespace: str, pair: tuple[str, str]) -> Optional[EmotionalVector]:
        """最新のベクトルを取得（ペア指定）"""
        ...

    @abc.abstractmethod
    def get_all(self, namespace: str) -> list[EmotionalVector]:
        """ネームスペース内の全ベクトル取得"""
        ...

    @abc.abstractmethod
    def delete(self, namespace: str, key: str) -> bool:
        """ベクトル削除"""
        ...

    @abc.abstractmethod
    def get_namespace_keys(self, namespace: str) -> list[str]:
        """ネームスペース内のキー一覧取得"""
        ...


class RedisVectorStore(VectorStore):
    """Redis実装のベクトルストア"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        default_ttl: int = 864000,  # 10日
        namespace_ttls: Optional[dict[str, int]] = None,
        skip_connection_check: bool = False,
        **kwargs,
    ):
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
            **kwargs,
        )
        self.default_ttl = default_ttl
        self.namespace_ttls = namespace_ttls or {}
        
        # 接続テスト（スキップ可能）
        if not skip_connection_check:
            try:
                self.client.ping()
            except redis.ConnectionError as e:
                logger.warning(f"Redis connection failed: {e}. Store will not be functional.")

    def _make_key(self, namespace: str, key: str) -> str:
        """Redisキー生成"""
        return f"emotional:{namespace}:{key}"

    def _get_ttl(self, namespace: str) -> int:
        """ネームスペース別TTL取得"""
        return self.namespace_ttls.get(namespace, self.default_ttl)

    def upsert(self, namespace: str, key: str, vector: EmotionalVector) -> None:
        """ベクトルをRedisに保存（JSONシリアライズ）"""
        redis_key = self._make_key(namespace, key)
        data = json.dumps(vector.to_dict(), ensure_ascii=False)
        ttl = self._get_ttl(namespace)
        
        try:
            if ttl > 0:
                self.client.set(redis_key, data, ex=ttl)
            else:
                self.client.set(redis_key, data)
            logger.debug(f"Stored vector: {redis_key}")
        except redis.RedisError as e:
            logger.error(f"Failed to store vector {redis_key}: {e}")
            raise

    def get_latest(self, namespace: str, pair: tuple[str, str]) -> Optional[EmotionalVector]:
        """指定ペアの最新ベクトルを取得
        
        キー形式:
        - ep{episode}:{source}->{target} (ペア別)
        - ep{episode} (エピソード全体のベクトル、複数ペア含む)
        """
        keys = self.get_namespace_keys(namespace)
        if not keys:
            return None
        
        # ペア接頭辞でフィルタ
        pair_prefix = f"{pair[0]}->{pair[1]}"
        matching_keys = [k for k in keys if pair_prefix in k or k.startswith("ep")]
        
        if not matching_keys:
            return None
        
        # エピソード番号でソートして最新を取得
        def extract_ep_num(key: str) -> int:
            parts = key.split(":")[0] if ":" in key else key
            if parts.startswith("ep"):
                try:
                    return int(parts[2:])
                except ValueError:
                    return 0
            return 0
        
        latest_key = max(matching_keys, key=extract_ep_num)
        vector = self._get_by_key(namespace, latest_key)
        
        if vector:
            # 指定ペアの感情のみを含む新しいベクトルを返す
            pair_emotions = vector.get_pair_emotions(pair[0], pair[1])
            if pair_emotions:
                result = EmotionalVector(episode_id=vector.episode_id)
                for emo, val in pair_emotions.items():
                    result.signals[(pair[0], pair[1], emo)] = val
                    result.confidences[(pair[0], pair[1], emo)] = vector.confidences.get((pair[0], pair[1], emo), 0.5)
                    result.causes[(pair[0], pair[1], emo)] = vector.causes.get((pair[0], pair[1], emo))
                return result
        return None

    def get_all(self, namespace: str) -> list[EmotionalVector]:
        """ネームスペース内の全ベクトル取得"""
        keys = self.get_namespace_keys(namespace)
        vectors = []
        for key in keys:
            vec = self._get_by_key(namespace, key)
            if vec:
                vectors.append(vec)
        return vectors

    def _get_by_key(self, namespace: str, key: str) -> Optional[EmotionalVector]:
        """キー指定でベクトル取得"""
        redis_key = self._make_key(namespace, key)
        try:
            data = self.client.get(redis_key)
            if data:
                return EmotionalVector.from_dict(json.loads(data))
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load vector {redis_key}: {e}")
        return None

    def delete(self, namespace: str, key: str) -> bool:
        """ベクトル削除"""
        redis_key = self._make_key(namespace, key)
        try:
            result = self.client.delete(redis_key)
            return result > 0
        except redis.RedisError as e:
            logger.error(f"Failed to delete vector {redis_key}: {e}")
            return False

    def get_namespace_keys(self, namespace: str) -> list[str]:
        """ネームスペース内のキー一覧取得（SCAN使用）"""
        pattern = self._make_key(namespace, "*")
        keys = []
        try:
            cursor = 0
            while True:
                cursor, batch = self.client.scan(cursor, match=pattern, count=100)
                # プレフィックスを除去してキー名のみ抽出
                prefix = f"emotional:{namespace}:"
                for k in batch:
                    if k.startswith(prefix):
                        keys.append(k[len(prefix):])
                if cursor == 0:
                    break
        except redis.RedisError as e:
            logger.error(f"Failed to scan keys for namespace {namespace}: {e}")
        return keys

    def close(self) -> None:
        """接続クローズ"""
        self.client.close()

    def __enter__(self) -> RedisVectorStore:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


# 後方互換性のためのエイリアス
VectorStore = VectorStore
RedisVectorStore = RedisVectorStore

__all__ = ["VectorStore", "RedisVectorStore"]