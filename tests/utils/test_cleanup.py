"""クリーンアップユーティリティの使用例を示すテスト.
 
クリーンアップユーティリティが正しく動作することを確認します。
"""
from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock
from tests.utils.cleanup import cleanup_redis_client, cleanup_chromadb_client, CleanupManager, run_cleanup_functions


def test_cleanup_redis_client():
    """Redis クリーンアップユーティリティをテスト."""
    # モック Redis クライアントを作成
    mock_redis = Mock()
    mock_redis.flushall = Mock()
    
    # クリーンアップを実行（例外が発生しないことを確認）
    cleanup_redis_client(mock_redis)
    mock_redis.flushall.assert_called_once()
    
    # None を渡しても例外が発生しないことを確認
    cleanup_redis_client(None)  # 例外が発生しないはず
    
    # flushall メソッドがないオブジェクトを渡しても例外が発生しないことを確認
    class NoFlushallClient:
        pass
    cleanup_redis_client(NoFlushallClient())  # 例外が発生しないはず


def test_cleanup_chromadb_client():
    """ChromaDB クリーンアップユーティリティをテスト."""
    # モック ChromaDB クライアントを作成
    mock_chromadb = Mock()
    mock_collection = Mock()
    mock_collection.name = "test_collection"
    mock_chromadb.list_collections.return_value = [mock_collection]
    mock_chromadb.delete_collection = Mock()
    
    # クリーンアップを実行（例外が発生しないことを確認）
    cleanup_chromadb_client(mock_chromadb)
    mock_chromadb.list_collections.assert_called_once()
    mock_chromadb.delete_collection.assert_called_once_with("test_collection")
    
    # None を渡しても例外が発生しないことを確認
    cleanup_chromadb_client(None)  # 例外が発生しないはず
    
    # 空のコレクションリストを返す場合
    mock_chromadb_empty = Mock()
    mock_chromadb_empty.list_collections.return_value = []
    mock_chromadb_empty.delete_collection = Mock()
    cleanup_chromadb_client(mock_chromadb_empty)
    mock_chromadb_empty.list_collections.assert_called_once()
    mock_chromadb_empty.delete_collection.assert_not_called()


def test_cleanup_manager():
    """CleanupManager コンテキストマネージャをテスト."""
    cleanup_called = []
    
    def cleanup_func_1():
        cleanup_called.append("func1")
    
    def cleanup_func_2():
        cleanup_called.append("func2")
    
    # CleanupManager を使用
    with CleanupManager() as cleanup:
        cleanup.add(cleanup_func_1)
        cleanup.add(cleanup_func_2)
        # ここでテストロジックを実行（今回は何もしない）
        assert cleanup_called == []  # まだクリーンアップは呼ばれていない
    
    # コンテキストを抜けた後、クリーンアップ関数が呼ばれていることを確認
    assert set(cleanup_called) == {"func1", "func2"}
    assert len(cleanup_called) == 2  # それぞれ一度だけ呼ばれている


def test_run_cleanup_functions():
    """run_cleanup_functions 関数をテスト."""
    cleanup_called = []
    
    def cleanup_func_1():
        cleanup_called.append("func1")
    
    def cleanup_func_2():
        cleanup_called.append("func2")
    
    # 例外が発生しないクリーンアップ関数
    cleanup_functions = [cleanup_func_1, cleanup_func_2]
    run_cleanup_functions(cleanup_functions)
    assert set(cleanup_called) == {"func1", "func2"}
    
    # 例外が発生するクリーンアップ関数を含む場合
    def cleanup_func_error():
        cleanup_called.append("error")
        raise ValueError("テスト用のエラー")
    
    cleanup_called.clear()
    cleanup_functions = [cleanup_func_1, cleanup_func_error, cleanup_func_2]
    # 例外が発生しても他の関数は実行されるべき
    run_cleanup_functions(cleanup_functions)
    assert "func1" in cleanup_called
    assert "error" in cleanup_called
    assert "func2" in cleanup_called