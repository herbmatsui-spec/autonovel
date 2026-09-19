"""Tests for Redis configuration."""
from __future__ import annotations

import pytest
import yaml


class TestRedisConfig:
    """Redis設定テスト"""

    def test_redis_config_loads(self):
        """Redis設定が読み込めること"""
        with open("config/redis.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        assert "redis" in config
        r = config["redis"]
        assert r["host"] == "localhost"
        assert r["port"] == 6379
        assert r["db"] == 0
        assert r["ttl_default"] == 864000
        assert "namespace_ttls" in r
        assert r["namespace_ttls"]["pipeline"] == 864000
        assert r["namespace_ttls"]["annotation"] == 0  # 無期限

    def test_env_override_documented(self):
        """環境変数上書きがドキュメント化されていること"""
        with open("config/redis.yaml", "r", encoding="utf-8") as f:
            content = f.read()
        assert "REDIS_URL" in content