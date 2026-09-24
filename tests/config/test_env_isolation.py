"""ローカル設定が本番環境に漏れないことをテスト"""
import os
from unittest.mock import patch
from src.config.env_loader import load_config

def test_local_config_does_not_leak_to_production():
    # 本番環境をシミュレート
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        prod_config = load_config()
    # ローカル環境をシミュレート
    with patch.dict(os.environ, {"ENVIRONMENT": "local"}):
        local_config = load_config()
    # 重要な違いをチェック
    assert prod_config["database"]["type"] == "postgresql"
    assert local_config["database"]["type"] == "sqlite"
    assert prod_config["log"]["level"] == "INFO"
    assert local_config["log"]["level"] == "DEBUG"