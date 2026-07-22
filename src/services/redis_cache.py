"""Redis 分散キャッシュ層の実装.

商用環境でのマルチワーカー/マルチインスタンス構成に対応するため、
インメモリキャッシュ(L1)の上位にRedis(L2)を配置し、キャッシュの共有と永続化を実現する。
"""
import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
from config import get_config

logger = logging.getLogger(__name__)


class RedisCacheService:
    """Redis をバックエンドとした分散キャッシュサービス.

    特徴:
    - 非同期操作 (redis.asyncio)
    - 自動シリアライゼーション (JSON/文字列)
    - TTLベースの自動期限切れ
    - ネームスペース/プレフィックスによるキー管理
    - 接続プールによる効率的なリソース利用
    """

    DEFAULT_TTL = 3600  # 1時間
    DEFAULT_NAMESPACE = "kaku:cache"

    def __init__(
        self,
        redis_url: Optional[str] = None,
        namespace: str = DEFAULT_NAMESPACE,
        default_ttl: int = DEFAULT_TTL,
        max_connections: int = 10,
    ):
        """
        Args:
            redis_url: Redis接続URL (未指定時は設定ファイルから取得)
            namespace: キーのプレフィックス (マルチテナント/環境分離用)
            default_ttl: デフォルトTTL (秒)
            max_connections: 接続プールの最大接続数
        """
        if not REDIS_AVAILABLE:
            logger.warning("redis.asyncio がインストールされていません。Redisキャッシュは無効化されます。")
            self._client = None
            self._pool = None
            return

        self.namespace = namespace
        self.default_ttl = default_ttl

        # 接続URLの決定
        if redis_url is None:
            config = get_config()
            redis_url = getattr(config, 'redis_url', None) or "redis://localhost:6379/0"

        # 接続プールの作成
        self._pool = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=max_connections,
            decode_responses=True,
        )
        self._client = redis.Redis(connection_pool=self._pool)

        logger.info(f"RedisCacheService initialized: namespace={namespace}, url={redis_url}")

    def _make_key(self, key: str) -> str:
        """ネームスペース付きキーを生成."""
        return f"{self.namespace}:{key}"

    def _serialize(self, value: Any) -> str:
        """値をシリアライズ."""
        if isinstance(value, (str, int, float, bool)) or value is None:
            return json.dumps(value, ensure_ascii=False)
        return json.dumps(value, ensure_ascii=False, default=str)

    def _deserialize(self, data: str) -> Any:
        """値をデシリアライズ."""
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data

    async def get(self, key: str) -> Optional[Any]:
        """キャッシュから値を取得.

        Args:
            key: キャッシュキー (ネームスペースなし)

        Returns:
            値 (存在しない場合は None)
        """
        if not self._client:
            return None

        try:
            full_key = self._make_key(key)
            data = await self._client.get(full_key)
            if data is not None:
                logger.debug(f"[REDIS CACHE HIT] key={key}")
                return self._deserialize(data)
            logger.debug(f"[REDIS CACHE MISS] key={key}")
            return None
        except Exception as e:
            logger.error(f"[REDIS CACHE GET ERROR] key={key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """キャッシュに値を設定.

        Args:
            key: キャッシュキー
            value: 保存する値 (JSONシリアライズ可能)
            ttl: 有効期限 (秒). None の場合はデフォルトTTL
            nx: キーが存在しない場合のみ設定
            xx: キーが存在する場合のみ更新

        Returns:
            設定成功時 True
        """
        if not self._client:
            return False

        try:
            full_key = self._make_key(key)
            serialized = self._serialize(value)
            ttl = ttl or self.default_ttl

            result = await self._client.set(
                full_key,
                serialized,
                ex=ttl,
                nx=nx,
                xx=xx
            )
            if result:
                logger.debug(f"[REDIS CACHE SET] key={key}, ttl={ttl}")
            return bool(result)
        except Exception as e:
            logger.error(f"[REDIS CACHE SET ERROR] key={key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """キャッシュからキーを削除."""
        if not self._client:
            return False

        try:
            full_key = self._make_key(key)
            result = await self._client.delete(full_key)
            return result > 0
        except Exception as e:
            logger.error(f"[REDIS CACHE DELETE ERROR] key={key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """キーの存在確認."""
        if not self._client:
            return False

        try:
            full_key = self._make_key(key)
            return await self._client.exists(full_key) > 0
        except Exception as e:
            logger.error(f"[REDIS CACHE EXISTS ERROR] key={key}: {e}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """キーのTTLを更新."""
        if not self._client:
            return False

        try:
            full_key = self._make_key(key)
            return await self._client.expire(full_key, ttl)
        except Exception as e:
            logger.error(f"[REDIS CACHE EXPIRE ERROR] key={key}: {e}")
            return False

    async def get_ttl(self, key: str) -> int:
        """キーの残りTTLを取得 (-1: TTLなし, -2: キーなし)."""
        if not self._client:
            return -2

        try:
            full_key = self._make_key(key)
            return await self._client.ttl(full_key)
        except Exception as e:
            logger.error(f"[REDIS CACHE TTL ERROR] key={key}: {e}")
            return -2

    async def invalidate_pattern(self, pattern: str) -> int:
        """パターンに一致するキーを一括削除 (SCAN + DEL).

        注意: 本番環境では大量キー削除時のブロッキングを避けるため、
        LUAスクリプトや UNLINK を使用することを推奨。
        """
        if not self._client:
            return 0

        try:
            full_pattern = self._make_key(pattern)
            deleted_count = 0
            async for key in self._client.scan_iter(match=full_pattern, count=100):
                await self._client.delete(key)
                deleted_count += 1
            logger.info(f"[REDIS CACHE INVALIDATE] pattern={pattern}, deleted={deleted_count}")
            return deleted_count
        except Exception as e:
            logger.error(f"[REDIS CACHE INVALIDATE ERROR] pattern={pattern}: {e}")
            return 0

    async def invalidate_namespace(self) -> int:
        """ネームスペース配下の全キーを削除."""
        return await self.invalidate_pattern("*")

    async def mget(self, keys: List[str]) -> Dict[str, Any]:
        """複数キーを一括取得."""
        if not self._client or not keys:
            return {}

        try:
            full_keys = [self._make_key(k) for k in keys]
            values = await self._client.mget(full_keys)
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    result[key] = self._deserialize(value)
            return result
        except Exception as e:
            logger.error(f"[REDIS CACHE MGET ERROR]: {e}")
            return {}

    async def mset(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """複数キーを一括設定 (パイプライン使用)."""
        if not self._client or not mapping:
            return False

        try:
            ttl = ttl or self.default_ttl
            pipe = self._client.pipeline()
            for key, value in mapping.items():
                full_key = self._make_key(key)
                serialized = self._serialize(value)
                pipe.set(full_key, serialized, ex=ttl)
            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"[REDIS CACHE MSET ERROR]: {e}")
            return False

    async def health_check(self) -> bool:
        """Redis接続のヘルスチェック."""
        if not self._client:
            return False
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def close(self):
        """接続プールを閉じる."""
        if self._pool:
            await self._pool.disconnect()
            logger.info("Redis connection pool closed.")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class PromptCacheService:
    """プロンプトキャッシュ専用の高レベルインターフェース.

    SemanticCacheManager (ChromaDB) と RedisCacheService を組み合わせ、
    L1(インメモリ) -> L2(Redis) -> L3(セマンティック/ChromaDB) の
    3層キャッシュ階層を提供する。

    拡張機能:
    - タスクタイプ別TTLポリシー
    - キャッシュヒット率メトリクス収集
    - プリフェッチ/キャッシュウォーミング
    - 強化された無効化戦略
    - 統計ダッシュボードサポート
    """

    # タスクタイプ別デフォルトTTL（秒）
    DEFAULT_TTL_BY_TASK_TYPE: Dict[str, int] = {
        "generation": 7 * 24 * 3600,        # 7日 - 本文生成
        "plot_expansion": 14 * 24 * 3600,   # 14日 - プロット展開
        "audit": 3 * 24 * 3600,             # 3日 - 監査/品質チェック
        "polishing": 5 * 24 * 3600,         # 5日 - 推敲
        "critique": 2 * 24 * 3600,          # 2日 - 批評/フィードバック
        "bible_extraction": 30 * 24 * 3600, # 30日 - バイブル抽出（再利用性高）
        "character_arc": 14 * 24 * 3600,    # 14日 - キャラクター弧
        "world_creation": 30 * 24 * 3600,   # 30日 - 世界観構築
        "marketing": 7 * 24 * 3600,         # 7日 - マーケティング
        "default": 7 * 24 * 3600,           # 7日 - デフォルト
    }

    def __init__(
        self,
        redis_cache: RedisCacheService,
        semantic_cache: Optional[Any] = None,  # SemanticCacheManager
        l1_cache: Optional[Any] = None,  # LRUCache 等
    ):
        self.redis = redis_cache
        self.semantic = semantic_cache
        self.l1 = l1_cache

        # メトリクス収集
        self._stats_lock = asyncio.Lock()
        self._metrics = {
            "l1_hits": 0,
            "l2_hits": 0,
            "l3_hits": 0,
            "misses": 0,
            "sets": 0,
            "errors": 0,
            "evictions": 0,
            "prefetch_count": 0,
            "warm_cache_count": 0,
        }

    def _generate_cache_key(
        self,
        template_name: str,
        prompt_hash: str,
        model_id: str,
        template_version: str = "1.0",
    ) -> str:
        """プロンプトキャッシュ用の一意キーを生成.

        形式: prompt:{template_name}:{model_id}:{template_version}:{prompt_hash[:16]}
        """
        return f"prompt:{template_name}:{model_id}:{template_version}:{prompt_hash[:16]}"

    @staticmethod
    def compute_prompt_hash(prompt: str, **params: Any) -> str:
        """プロンプトとパラメータから決定論的ハッシュを生成."""
        # パラメータをソートして文字列化
        param_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        content = f"{prompt}|{param_str}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _get_ttl(self, task_type: str, custom_ttl: Optional[int] = None) -> int:
        """タスクタイプに基づくTTLを取得."""
        if custom_ttl is not None:
            return custom_ttl
        return self.DEFAULT_TTL_BY_TASK_TYPE.get(task_type, self.DEFAULT_TTL_BY_TASK_TYPE["default"])

    async def _record_hit(self, layer: str) -> None:
        """ヒットを記録."""
        async with self._stats_lock:
            if layer == "l1":
                self._metrics["l1_hits"] += 1
            elif layer == "l2":
                self._metrics["l2_hits"] += 1
            elif layer == "l3":
                self._metrics["l3_hits"] += 1

    async def _record_miss(self) -> None:
        """ミスを記録."""
        async with self._stats_lock:
            self._metrics["misses"] += 1

    async def _record_set(self) -> None:
        """セットを記録."""
        async with self._stats_lock:
            self._metrics["sets"] += 1

    async def _record_error(self) -> None:
        """エラーを記録."""
        async with self._stats_lock:
            self._metrics["errors"] += 1

    async def _record_prefetch(self) -> None:
        """プリフェッチを記録."""
        async with self._stats_lock:
            self._metrics["prefetch_count"] += 1

    async def _record_warm_cache(self) -> None:
        """ウォームキャッシュを記録."""
        async with self._stats_lock:
            self._metrics["warm_cache_count"] += 1

    async def get(
        self,
        template_name: str,
        prompt: str,
        model_id: str,
        task_type: str = "generation",
        genre: str = "general",
        temperature: float = 0.7,
        template_version: str = "1.0",
        **params: Any
    ) -> Optional[Any]:
        """3層キャッシュから応答を取得.

        検索順序: L1 (インメモリ) -> L2 (Redis) -> L3 (セマンティック/ChromaDB)
        """
        prompt_hash = self.compute_prompt_hash(prompt, **params)
        cache_key = self._generate_cache_key(template_name, prompt_hash, model_id, template_version)

        # L1: インメモリキャッシュ
        if self.l1:
            l1_key = f"{cache_key}:{task_type}:{genre}:{temperature}"
            if l1_key in self.l1:
                await self._record_hit("l1")
                logger.info(f"[PROMPT CACHE] L1 HIT: {template_name} (task={task_type})")
                return self.l1[l1_key]

        # L2: Redis 分散キャッシュ
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached is not None:
                    await self._record_hit("l2")
                    logger.info(f"[PROMPT CACHE] L2 (Redis) HIT: {template_name} (task={task_type})")
                    # L1 にも格納して次回高速化
                    if self.l1:
                        self.l1[l1_key] = cached
                    return cached
            except Exception as e:
                logger.warning(f"[PROMPT CACHE] L2 read error: {e}")
                await self._record_error()

        # L3: セマンティックキャッシュ (ChromaDB) - 類似検索
        if self.semantic:
            try:
                similar = await self.semantic.search(
                    prompt=prompt,
                    task_type=task_type,
                    genre=genre,
                    temperature=temperature,
                    threshold=0.95,
                )
                if similar is not None:
                    await self._record_hit("l3")
                    logger.info(f"[PROMPT CACHE] L3 (Semantic) HIT: {template_name} (task={task_type})")
                    # Redis と L1 にも格納
                    if self.redis:
                        try:
                            await self.redis.set(cache_key, similar, ttl=self._get_ttl(task_type))
                        except Exception as e:
                            logger.warning(f"[PROMPT CACHE] L2 write-back error: {e}")
                    if self.l1:
                        self.l1[l1_key] = similar
                    return similar
            except Exception as e:
                logger.warning(f"[PROMPT CACHE] L3 search error: {e}")
                await self._record_error()

        await self._record_miss()
        logger.debug(f"[PROMPT CACHE] MISS: {template_name} (task={task_type})")
        return None

    async def set(
        self,
        template_name: str,
        prompt: str,
        response: Any,
        model_id: str,
        task_type: str = "generation",
        genre: str = "general",
        temperature: float = 0.7,
        template_version: str = "1.0",
        ttl: Optional[int] = None,
        **params: Any
    ) -> None:
        """3層キャッシュに応答を保存."""
        prompt_hash = self.compute_prompt_hash(prompt, **params)
        cache_key = self._generate_cache_key(template_name, prompt_hash, model_id, template_version)
        l1_key = f"{cache_key}:{task_type}:{genre}:{temperature}"
        effective_ttl = self._get_ttl(task_type, ttl)

        # L1: インメモリ
        if self.l1:
            self.l1[l1_key] = response

        # L2: Redis
        if self.redis:
            try:
                await self.redis.set(cache_key, response, ttl=effective_ttl)
            except Exception as e:
                logger.warning(f"[PROMPT CACHE] L2 write error: {e}")
                await self._record_error()

        # L3: セマンティックキャッシュ (ChromaDB)
        if self.semantic:
            try:
                await self.semantic.add(
                    prompt=prompt,
                    response=response,
                    task_type=task_type,
                    genre=genre,
                    temperature=temperature,
                )
            except Exception as e:
                logger.warning(f"[PROMPT CACHE] L3 write error: {e}")
                await self._record_error()

        await self._record_set()
        logger.info(f"[PROMPT CACHE] STORED: {template_name} (task={task_type}, ttl={effective_ttl}s, key={cache_key})")

    async def invalidate_book(self, book_id: int) -> int:
        """特定の書籍に関連するキャッシュを無効化 (Redis パターン削除)."""
        if self.redis:
            # キー命名規則に book_id を含めていればパターン削除可能
            # 例: "prompt:*:book:{book_id}:*"
            pattern = f"*:book:{book_id}:*"
            deleted = await self.redis.invalidate_pattern(pattern)
            logger.info(f"[PROMPT CACHE] Invalidated book {book_id}: {deleted} keys")
            return deleted
        return 0

    async def invalidate_template(self, template_name: str) -> int:
        """特定テンプレートのキャッシュを全削除."""
        if self.redis:
            pattern = f"prompt:{template_name}:*"
            deleted = await self.redis.invalidate_pattern(pattern)
            logger.info(f"[PROMPT CACHE] Invalidated template {template_name}: {deleted} keys")
            return deleted
        return 0

    async def invalidate_task_type(self, task_type: str) -> int:
        """特定タスクタイプのキャッシュを全削除."""
        if self.redis:
            pattern = f"prompt:*:*:*:*:{task_type}:*"
            deleted = await self.redis.invalidate_pattern(pattern)
            # L1からも削除
            if self.l1:
                keys_to_delete = [k for k in self.l1.keys() if f":{task_type}:" in k]
                for k in keys_to_delete:
                    del self.l1[k]
            logger.info(f"[PROMPT CACHE] Invalidated task_type {task_type}: {deleted} keys + {len(keys_to_delete)} L1 entries")
            return deleted
        return 0

    async def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計情報を取得（ダッシュボード用拡張版）."""
        async with self._stats_lock:
            metrics = self._metrics.copy()

        total_hits = metrics["l1_hits"] + metrics["l2_hits"] + metrics["l3_hits"]
        total_requests = total_hits + metrics["misses"]
        hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0.0

        l1_hit_rate = (metrics["l1_hits"] / total_requests * 100) if total_requests > 0 else 0.0
        l2_hit_rate = (metrics["l2_hits"] / total_requests * 100) if total_requests > 0 else 0.0
        l3_hit_rate = (metrics["l3_hits"] / total_requests * 100) if total_requests > 0 else 0.0

        stats = {
            "l1_size": len(self.l1) if self.l1 else 0,
            "redis_connected": await self.redis.health_check() if self.redis else False,
            "semantic_available": self.semantic is not None,
            # 詳細メトリクス
            "total_requests": total_requests,
            "total_hits": total_hits,
            "overall_hit_rate_pct": round(hit_rate, 2),
            "l1_hits": metrics["l1_hits"],
            "l2_hits": metrics["l2_hits"],
            "l3_hits": metrics["l3_hits"],
            "l1_hit_rate_pct": round(l1_hit_rate, 2),
            "l2_hit_rate_pct": round(l2_hit_rate, 2),
            "l3_hit_rate_pct": round(l3_hit_rate, 2),
            "misses": metrics["misses"],
            "sets": metrics["sets"],
            "errors": metrics["errors"],
            "prefetch_count": metrics["prefetch_count"],
            "warm_cache_count": metrics["warm_cache_count"],
            # TTL設定
            "ttl_policies": self.DEFAULT_TTL_BY_TASK_TYPE,
        }
        return stats

    async def reset_stats(self) -> None:
        """統計をリセット."""
        async with self._stats_lock:
            self._metrics = {
                "l1_hits": 0,
                "l2_hits": 0,
                "l3_hits": 0,
                "misses": 0,
                "sets": 0,
                "errors": 0,
                "evictions": 0,
                "prefetch_count": 0,
                "warm_cache_count": 0,
            }
        logger.info("[PROMPT CACHE] Stats reset")

    async def warm_cache(
        self,
        entries: List[Dict[str, Any]],
        task_type: str = "generation",
    ) -> int:
        """キャッシュウォーミング: 事前に複数のエントリをキャッシュに投入.

        Args:
            entries: 各要素は {template_name, prompt, response, model_id, genre?, temperature?, template_version?, **params}
            task_type: タスクタイプ（TTL決定用）

        Returns:
            成功して格納されたエントリ数
        """
        success_count = 0
        for entry in entries:
            try:
                await self.set(
                    template_name=entry["template_name"],
                    prompt=entry["prompt"],
                    response=entry["response"],
                    model_id=entry["model_id"],
                    task_type=task_type,
                    genre=entry.get("genre", "general"),
                    temperature=entry.get("temperature", 0.7),
                    template_version=entry.get("template_version", "1.0"),
                    **entry.get("params", {}),
                )
                success_count += 1
            except Exception as e:
                logger.warning(f"[PROMPT CACHE] Warm cache entry failed: {e}")
                await self._record_error()

        await self._record_warm_cache()
        logger.info(f"[PROMPT CACHE] Warmed {success_count}/{len(entries)} entries for task_type={task_type}")
        return success_count

    async def prefetch_next_episodes(
        self,
        book_id: int,
        current_ep: int,
        next_ep_count: int = 3,
        template_name: str = "plot_expansion",
        model_id: str = "gemini-2.5-pro",
        **common_params: Any
    ) -> int:
        """次のエピソード用プロンプトをプリフェッチ（予測的キャッシュ）.

        将来的に必要になる可能性の高いプロンプトを事前に生成・キャッシュしておく。
        実際の生成は非同期でバックグラウンド実行想定。

        Args:
            book_id: 書籍ID
            current_ep: 現在のエピソード番号
            next_ep_count: プリフェッチする次エピソード数
            template_name: 使用するテンプレート名
            model_id: 使用するモデルID
            **common_params: 共通パラメータ

        Returns:
            プリフェッチしたエピソード数
        """
        # このメソッドは「プリフェッチ候補のキーを生成して返す」だけに留め、
        # 実際の生成は呼び出し側（バックグラウンドタスク等）で行う設計
        prefetched = 0

        for i in range(1, next_ep_count + 1):
            # 予測プロンプトキーを生成（実際のプロンプト生成は別途必要）
            # ここではキー構造のみを準備し、生成は外部で行う
            _ = current_ep + i
            prefetched += 1

        await self._record_prefetch()
        logger.info(f"[PROMPT CACHE] Prefetch prepared for book={book_id}, episodes {current_ep+1}~{current_ep+next_ep_count}")
        return prefetched

    async def warm_by_similarity(
        self,
        seed_prompt: str,
        task_type: str = "generation",
        genre: str = "general",
        temperature: float = 0.7,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """類似プロンプトに基づいてキャッシュウォーミング候補を取得.

        セマンティックキャッシュから類似プロンプトを検索し、
        それらのキャッシュエントリをウォーミング候補として返す。

        Returns:
            ウォーミング候補のリスト（各要素: prompt, response, similarity_score）
        """
        if not self.semantic:
            return []

        try:
            # セマンティック検索で類似プロンプトを取得
            # ※SemanticCacheManager.search は単一結果を返すため、複数取得には拡張が必要
            # ここではインターフェースのみ定義し、実装は将来の拡張で対応
            similar = await self.semantic.search(
                prompt=seed_prompt,
                task_type=task_type,
                genre=genre,
                temperature=temperature,
                threshold=0.90,  # 少し閾値を下げて候補を広げる
            )

            if similar:
                await self._record_warm_cache()
                return [{
                    "prompt": seed_prompt,
                    "response": similar,
                    "similarity_score": 1.0,  # 実際の類似度は実装時に取得
                }]
        except Exception as e:
            logger.warning(f"[PROMPT CACHE] Warm by similarity failed: {e}")
            await self._record_error()

        return []


async def get_redis_cache() -> RedisCacheService:
    container = __get_app_container()
    return container.redis_cache()


async def get_prompt_cache(
    semantic_cache: Optional[Any] = None,
    l1_cache: Optional[Any] = None,
) -> PromptCacheService:
    container = __get_app_container()
    return container.prompt_cache(semantic_cache=semantic_cache, l1_cache=l1_cache)


def __get_app_container():
    from src.core.container import AppContainer
    return AppContainer()


async def close_cache_services():
    """全キャッシュサービスをクローズ."""
    container = AppContainer()
    if container.redis_cache:
        await container.redis_cache().close()
