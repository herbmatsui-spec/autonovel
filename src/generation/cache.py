import time
import threading
from typing import Any, Optional, Tuple


class GenerationCache:
    """
    シンプルなインメモリーキャッシュ（TTLサポート付き）。
    キー: プロンプトハッシュ + パラメータハッシュ + シード（もしあれば）
    値: 生成結果テキスト
    TTL（Time To Live）機能オプション
    キャッシュヒット率を測定するメトリクス
    """

    def __init__(self, default_ttl: Optional[float] = None):
        """
        キャッシュを初期化。
        
        Args:
            default_ttl: デフォルトのTTL（秒）。Noneの場合はTTLなし（無期限）。
        """
        self._cache: dict = {}
        self._lock = threading.RLock()  # 再入可能ロックで再帰的な呼び出しにも対応
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
    
    def _is_expired(self, expiry: Optional[float]) -> bool:
        """エントリが期限切れかどうかをチェック"""
        if expiry is None:
            return False
        return time.time() > expiry
    
    def set(self, key: Any, value: Any, ttl: Optional[float] = None) -> None:
        """
        キーと値をキャッシュに保存する。
        
        Args:
            key: キャッシュキー（ハッシュ可能なオブジェクト）
            value: キャッシュする値
            ttl: TTL（秒）。Noneの場合はdefault_ttlを使用。
        """
        with self._lock:
            if ttl is None:
                ttl = self._default_ttl
            
            expiry = time.time() + ttl if ttl is not None else None
            self._cache[key] = (value, expiry, 0)  # (value, expiry, hit_count)
    
    def get(self, key: Any) -> Tuple[bool, Any]:
        """
        キーから値を取得する。
        
        Args:
            key: キャッシュキー
            
        Returns:
            (found, value) のタプル。
            found: True if key exists and not expired, False otherwise.
            value: 見つかった場合の値、見つからなかった場合はNone。
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return False, None
            
            value, expiry, hit_count = entry
            if self._is_expired(expiry):
                # 期限切れなら削除してミスとする
                del self._cache[key]
                self._misses += 1
                return False, None
            
            # ヒットカウントを増やす
            self._cache[key] = (value, expiry, hit_count + 1)
            self._hits += 1
            return True, value
    
    def delete(self, key: Any) -> bool:
        """
        キーを削除する。
        
        Args:
            key: 削除するキー
            
        Returns:
            True if key existed and was deleted, False otherwise.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """キャッシュをクリアする"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def hit_rate(self) -> float:
        """
        キャッシュヒット率を返す（0.0〜1.0）。
        
        Returns:
            ヒット率。ヒット+ミスが0の場合は0.0を返す。
        """
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total
    
    def stats(self) -> dict:
        """キャッシュの統計情報を返す"""
        with self._lock:
            return {
                "size": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": self.hit_rate(),
            }


# グローバルインスタンス（オプション）
default_cache = GenerationCache()


if __name__ == "__main__":
    # 簡単な動作テスト
    cache = GenerationCache(default_ttl=10.0)  # 10秒TTL
    
    # テスト: ミスからヒットへ
    key = ("prompt_hash", "param_hash")
    value = "Generated text"
    
    found, val = cache.get(key)
    print(f"初期取得: found={found}, value={val}")  # False, None
    
    cache.set(key, value)
    found, val = cache.get(key)
    print(f"保存後取得: found={found}, value={val}")  # True, "Generated text"
    print(f"ヒット率: {cache.hit_rate():.2f}")  # 0.5 (1ヒット, 1ミス)
    
    # 別キーはミス
    found, val = cache.get(("other", "hash"))
    print(f"別キー取得: found={found}, value={val}")  # False, None
    print(f"ヒット率: {cache.hit_rate():.2f}")  # 0.333... (1ヒット, 2ミス)
    
    # TTLテスト
    print("\n--- TTLテスト ---")
    short_cache = GenerationCache(default_ttl=0.1)  # 0.1秒TTL
    short_cache.set("ttl_key", "ttl_value")
    found, val = short_cache.get("ttl_key")
    print(f"即時取得: found={found}, value={val}")  # True, "ttl_value"
    time.sleep(0.2)
    found, val = short_cache.get("ttl_key")
    print(f"0.2秒後取得: found={found}, value={val}")  # False, None