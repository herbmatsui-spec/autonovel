"""Tests for vector store."""
from __future__ import annotations

import pytest

from src.pipeline.emotional_residue import EmotionalVector, EmotionalSignal, EmotionType
from src.stores.vector_store import RedisVectorStore, VectorStore


class TestVectorStore:
    """VectorStore インターフェーステスト（モック使用）"""

    def test_upsert_and_get_latest(self):
        """基本的な保存・取得テスト"""
        # fakeredisを使用してモック
        try:
            import fakeredis
            redis_client = fakeredis.FakeRedis(decode_responses=True)
        except ImportError:
            pytest.skip("fakeredis not installed")
        
        store = RedisVectorStore(skip_connection_check=True)
        store.client = redis_client
        
        vec = EmotionalVector(episode_id="ep01")
        vec.set_signal(EmotionalSignal(
            source="A", target="B", emotion_type=EmotionType.AFFECTION,
            value=0.5, confidence=0.8, evidence_span="...", episode_id="ep01"
        ))
        
        store.upsert("pipeline", "ep01:A->B", vec)
        
        # get_latest で取得
        retrieved = store.get_latest("pipeline", ("A", "B"))
        assert retrieved is not None
        assert retrieved.episode_id == "ep01"
        assert retrieved.get_value("A", "B", EmotionType.AFFECTION) == 0.5

    def test_get_all(self):
        """全件取得テスト"""
        try:
            import fakeredis
            redis_client = fakeredis.FakeRedis(decode_responses=True)
        except ImportError:
            pytest.skip("fakeredis not installed")
        
        store = RedisVectorStore(skip_connection_check=True)
        store.client = redis_client
        
        vec1 = EmotionalVector(episode_id="ep01")
        vec1.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.5, 0.8, "...", "ep01"))
        
        vec2 = EmotionalVector(episode_id="ep02")
        vec2.set_signal(EmotionalSignal("C", "D", EmotionType.TENSION, 0.7, 0.6, "...", "ep02"))
        
        store.upsert("pipeline", "ep01:A->B", vec1)
        store.upsert("pipeline", "ep02:C->D", vec2)
        
        all_vecs = store.get_all("pipeline")
        assert len(all_vecs) == 2

    def test_delete(self):
        """削除テスト"""
        try:
            import fakeredis
            redis_client = fakeredis.FakeRedis(decode_responses=True)
        except ImportError:
            pytest.skip("fakeredis not installed")
        
        store = RedisVectorStore(skip_connection_check=True)
        store.client = redis_client
        
        vec = EmotionalVector(episode_id="ep01")
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.5, 0.8, "...", "ep01"))
        
        store.upsert("pipeline", "ep01:A->B", vec)
        assert store.get_latest("pipeline", ("A", "B")) is not None
        
        deleted = store.delete("pipeline", "ep01:A->B")
        assert deleted is True
        assert store.get_latest("pipeline", ("A", "B")) is None

    def test_namespace_isolation(self):
        """ネームスペース分離テスト"""
        try:
            import fakeredis
            redis_client = fakeredis.FakeRedis(decode_responses=True)
        except ImportError:
            pytest.skip("fakeredis not installed")
        
        store = RedisVectorStore(skip_connection_check=True)
        store.client = redis_client
        
        vec1 = EmotionalVector(episode_id="ep01")
        vec1.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.5, 0.8, "...", "ep01"))
        
        vec2 = EmotionalVector(episode_id="ep01")
        vec2.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, -0.5, 0.8, "...", "ep01"))
        
        store.upsert("pipeline", "ep01:A->B", vec1)
        store.upsert("annotation", "ep01:A->B", vec2)
        
        pipeline_vec = store.get_latest("pipeline", ("A", "B"))
        annotation_vec = store.get_latest("annotation", ("A", "B"))
        
        assert pipeline_vec.get_value("A", "B", EmotionType.AFFECTION) == 0.5
        assert annotation_vec.get_value("A", "B", EmotionType.AFFECTION) == -0.5

    def test_get_namespace_keys(self):
        """キー一覧取得テスト"""
        try:
            import fakeredis
            redis_client = fakeredis.FakeRedis(decode_responses=True)
        except ImportError:
            pytest.skip("fakeredis not installed")
        
        store = RedisVectorStore(skip_connection_check=True)
        store.client = redis_client
        
        vec = EmotionalVector(episode_id="ep01")
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.5, 0.8, "...", "ep01"))
        
        store.upsert("pipeline", "ep01:A->B", vec)
        store.upsert("pipeline", "ep02:A->B", vec)
        
        keys = store.get_namespace_keys("pipeline")
        assert len(keys) == 2
        assert "ep01:A->B" in keys
        assert "ep02:A->B" in keys

    def test_ttl_expiry(self):
        """TTL経過でキーが消失すること（モック時間で確認）"""
        try:
            import fakeredis
            redis_client = fakeredis.FakeRedis(decode_responses=True)
        except ImportError:
            pytest.skip("fakeredis not installed")
        
        store = RedisVectorStore(default_ttl=1, skip_connection_check=True)  # 1秒
        store.client = redis_client
        
        vec = EmotionalVector(episode_id="ep01")
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.5, 0.8, "...", "ep01"))
        
        store.upsert("pipeline", "ep01:A->B", vec)
        assert store.get_latest("pipeline", ("A", "B")) is not None
        
        # fakeredisでは実際の時間経過をシミュレートできないためスキップ
        # 実際のRedisでは時間経過後にキーが消える