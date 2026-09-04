"""テストクリーンアップユーティリティ.
 
統合テストで使用する共通のクリーンアップ関数を提供します。
"""
from __future__ import annotations

import logging
from typing import Any, Callable, List


logger = logging.getLogger(__name__)


def cleanup_redis_client(redis_client) -> None:
    """Redis クライアントのデータをすべて削除.
    
    Args:
        redis_client: クリーンアップする Redis クライアントインスタンス
    """
    try:
        if redis_client:
            redis_client.flushall()
            logger.debug("Redis データをフラッシュしました")
    except Exception as e:
        logger.warning(f"Redis クリーンアップ中にエラーが発生しました: {e}")


def cleanup_chromadb_client(chromadb_client) -> None:
    """ChromaDB クライアントのすべてのコレクションを削除.
    
    Args:
        chromadb_client: クリーンアップする ChromaDB クライアントインスタンス
    """
    try:
        if chromadb_client:
            # ChromaDB クライアントが None の場合はスキップ
            if chromadb_client is not None:
                collections = chromadb_client.list_collections()
                for collection in collections:
                    chromadb_client.delete_collection(collection.name)
                logger.debug(f"{len(collections)} 個の ChromaDB コレクションを削除しました")
    except Exception as e:
        logger.warning(f"ChromaDB クリーンアップ中にエラーが発生しました: {e}")


def run_cleanup_functions(cleanup_functions: List[Callable[[], None]]) -> None:
    """複数のクリーンアップ関数を順番に実行.
    
    Args:
        cleanup_functions: 実行するクリーンアップ関数のリスト
    """
    for cleanup_func in cleanup_functions:
        try:
            cleanup_func()
        except Exception as e:
            logger.warning(f"クリーンアップ関数 {cleanup_func.__name__} の実行中にエラーが発生しました: {e}")


class CleanupManager:
    """クリーンアップ関数を管理するコンテキストマネージャ.
    
    使用例:
    with CleanupManager() as cleanup:
        cleanup.add(cleanup_redis_client, redis_client)
        cleanup.add(cleanup_chromadb_client, chromadb_client)
        # テストコードをここに書く
        # 自動的にクリーンアップが実行される
    """
    
    def __init__(self):
        self._cleanup_functions: List[Callable[[], None]] = []
    
    def add(self, func: Callable[..., None], *args, **kwargs) -> None:
        """クリーンアップ関数とその引数を追加.
        
        Args:
            func: 実行するクリーンアップ関数
            *args: 関数に渡す位置引数
            **kwargs: 関数に渡すキーワード引数
        """
        def wrapped_func():
            func(*args, **kwargs)
        self._cleanup_functions.append(wrapped_func)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストを終了するときにすべてのクリーンアップ関数を実行."""
        run_cleanup_functions(self._cleanup_functions)
        # 例外を伝播させる
        return False


# 便利なデコレータ
def with_cleanup(*cleanup_funcs):
    """テスト関数にクリーンアップを自動的に追加するデコレータ.
    
    使用例:
    @with_cleanup(cleanup_redis_client, redis_client Fox)
    def test_something():
        # テストコード
        pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            finally:
                run_cleanup_functions(list(cleanup_funcs))
        return wrapper
    return decorator