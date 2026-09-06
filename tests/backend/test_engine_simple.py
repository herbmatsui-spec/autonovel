import pytest
from src.backend.engine import UltimateHegemonyEngine

def test_engine_import_and_instantiation():
    """エンジンがインポートできてインスタンス化できることを確認するシンプルなテスト"""
    engine = UltimateHegemonyEngine(api_key="test-key")
    assert engine is not None
    assert engine.api_key == "test-key"