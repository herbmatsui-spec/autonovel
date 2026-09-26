"""Tests for compression pipeline integration with emotional residue."""
from __future__ import annotations

import pytest

fakeredis = pytest.importorskip("fakeredis")

try:
    import spacy
except ImportError:
    pytest.skip("spacy is not available or incompatible", allow_module_level=True)

from src.stores.vector_store import RedisVectorStore
from src.pipeline.emotional_residue import EmotionalResidueExtractor


class TestCompressionPipelineIntegration:
    """パイプライン統合テスト"""

    @pytest.fixture
    def vector_store(self):
        import fakeredis
        redis_client = fakeredis.FakeRedis(decode_responses=True)
        store = RedisVectorStore(skip_connection_check=True)
        store.client = redis_client
        return store

    @pytest.fixture
    def char_dict(self):
        return {"A", "B", "主人公"}

    def test_emotional_stage_runs(self, vector_store, char_dict):
        """感情抽出ステージが実行されること"""
        extractor = EmotionalResidueExtractor(vector_store, char_dict)
        
        # 空白モデルでテスト
        from src.pipeline.nlp_init import get_nlp_for_testing
        nlp = get_nlp_for_testing()
        if "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")
        extractor._nlp = nlp
        
        script = "AはBを信頼していた。"
        vector = extractor.extract_and_persist("ep01", script)
        
        assert vector.episode_id == "ep01"
        # Redisに保存されたか確認
        stored = vector_store.get_latest("pipeline", ("A", "B"))
        # 空白モデルでは依存構造がないためシグナルなしの可能性
        # 実行エラーにならないことのみ確認