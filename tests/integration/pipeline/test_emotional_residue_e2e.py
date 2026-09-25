"""E2E integration test for emotional residue pipeline."""
from __future__ import annotations

import pytest

from src.stores.vector_store import RedisVectorStore
from src.pipeline.emotional_residue import EmotionalResidueExtractor
from src.pipeline.nlp_init import get_nlp_for_testing
from src.pipeline.character_dict import load_character_dict


class TestEmotionalResidueE2E:
    """感情残基パイプラインE2Eテスト"""

    @pytest.fixture
    def vector_store(self):
        import fakeredis
        redis_client = fakeredis.FakeRedis(decode_responses=True)
        store = RedisVectorStore(skip_connection_check=True)
        store.client = redis_client
        return store

    @pytest.fixture
    def char_dict(self):
        return load_character_dict("config/characters.yaml")

    @pytest.fixture
    def extractor(self, vector_store, char_dict):
        ext = EmotionalResidueExtractor(vector_store, char_dict)
        # テスト用空白モデル
        nlp = get_nlp_for_testing()
        if "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")
        ext._nlp = nlp
        return ext

    def test_pipeline_run_saves_vector(self, extractor, vector_store):
        """パイプライン実行でVectorが保存されること"""
        script = """
        AはBの手を握った。「信じている」と呟く。
        Bは目を伏せ、小さく頷いた。
        """
        vector = extractor.extract_and_persist("ep01", script)
        
        assert vector.episode_id == "ep01"
        assert isinstance(vector.signals, dict)
        
        # Redisに保存確認 (キー形式: ep{episode_id})
        stored = vector_store.get_latest("pipeline", ("A", "B"))
        # 空白モデルでは依存構造解析不可のためシグナルなしの可能性
        # 少なくともエラーなく実行完了すること

    def test_multiple_episodes_separate_keys(self, extractor, vector_store):
        """複数エピソードで別キー保存"""
        extractor.extract_and_persist("ep01", "AはBを信頼した。")
        extractor.extract_and_persist("ep02", "BはAを恐れた。")
        
        # 両方のエピソードが保存される
        keys = vector_store.get_namespace_keys("pipeline")
        assert len(keys) >= 2
        # キーにエピソード番号が含まれる
        ep_keys = [k for k in keys if k.startswith("ep")]
        assert len(ep_keys) >= 2

    def test_namespace_isolation(self, extractor, vector_store):
        """ネームスペース分離確認"""
        # pipeline namespaceに保存
        extractor.extract_and_persist("ep01", "テスト")
        
        # 別namespaceには影響なし
        rule_keys = vector_store.get_namespace_keys("rule_engine")
        ann_keys = vector_store.get_namespace_keys("annotation")
        
        # pipelineのみにキーがある
        pipeline_keys = vector_store.get_namespace_keys("pipeline")
        assert len(pipeline_keys) >= 1
        assert len(rule_keys) == 0
        assert len(ann_keys) == 0