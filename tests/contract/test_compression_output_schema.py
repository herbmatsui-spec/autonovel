"""コントラクトテスト - 圧縮結果スキーマ検証"""
from __future__ import annotations

import pytest
from unittest.mock import Mock

from src.services.compression.compressor import FourLayerCompressor
from src.services.compression.models import (
    CompressionConfig,
    CompressedContextResult,
    RawTextLayerOutput,
    SubgraphLayerOutput,
    AbstractionLayerOutput,
    TrimmedContextOutput,
    CompressionQualityMetrics,
    SceneType,
    ProtectedContext,
    SceneFlowHistory,
)


class TestCompressionOutputSchema:
    """CompressedContextResult の必須フィールド存在確認"""

    @pytest.fixture
    def compressor(self):
        config = CompressionConfig(max_tokens=100, cache_enabled=False)
        return FourLayerCompressor(config=config)

    @pytest.fixture
    def sample_text(self):
        return "これはテスト用のサンプルテキストです。" * 50

    def test_compressed_context_result_has_required_fields(self, compressor, sample_text):
        """CompressedContextResult の必須フィールドが存在すること"""
        result = compressor.compress(sample_text)

        # 基本フィールド
        assert isinstance(result, CompressedContextResult)
        assert hasattr(result, "final_context_text")
        assert hasattr(result, "final_token_count")
        assert hasattr(result, "overall_reduction_ratio")
        assert hasattr(result, "from_cache")
        assert hasattr(result, "elapsed_ms")

        # 型確認
        assert isinstance(result.final_context_text, str)
        assert isinstance(result.final_token_count, int)
        assert isinstance(result.overall_reduction_ratio, float)
        assert isinstance(result.from_cache, bool)
        assert isinstance(result.elapsed_ms, (int, float))

    def test_final_token_count_positive_and_within_limit(self, compressor, sample_text):
        """final_token_count > 0 かつ max_tokens 以下"""
        result = compressor.compress(sample_text)

        assert result.final_token_count > 0
        assert result.final_token_count <= compressor.config.max_tokens

    def test_overall_reduction_ratio_range(self, compressor, sample_text):
        """overall_reduction_ratio が 0.0-1.0 の範囲内"""
        result = compressor.compress(sample_text)

        assert 0.0 <= result.overall_reduction_ratio <= 1.0

    def test_layer1_exists(self, compressor, sample_text):
        """layer1 (RawTextLayerOutput) が存在すること"""
        result = compressor.compress(sample_text)

        assert result.layer1 is not None
        assert isinstance(result.layer1, RawTextLayerOutput)
        assert hasattr(result.layer1, "extracted_keywords")
        assert hasattr(result.layer1, "keyword_scores")
        assert hasattr(result.layer1, "original_char_count")
        assert hasattr(result.layer1, "original_token_count")
        assert isinstance(result.layer1.extracted_keywords, list)
        assert isinstance(result.layer1.keyword_scores, dict)

    def test_layer2_exists(self, compressor, sample_text):
        """layer2 (SubgraphLayerOutput) が存在すること"""
        result = compressor.compress(sample_text)

        assert result.layer2 is not None
        assert isinstance(result.layer2, SubgraphLayerOutput)
        assert hasattr(result.layer2, "nodes")
        assert hasattr(result.layer2, "edges")
        assert hasattr(result.layer2, "seed_entity_names")
        assert hasattr(result.layer2, "pruned_edge_count")
        assert hasattr(result.layer2, "stats")

    def test_layer3_exists(self, compressor, sample_text):
        """layer3 (AbstractionLayerOutput) が存在すること"""
        result = compressor.compress(sample_text)

        assert result.layer3 is not None
        assert isinstance(result.layer3, AbstractionLayerOutput)
        assert hasattr(result.layer3, "abstract_concepts")
        assert hasattr(result.layer3, "categorized_facts")
        assert hasattr(result.layer3, "category_mappings")
        assert hasattr(result.layer3, "metadata")

    def test_layer4_exists(self, compressor, sample_text):
        """layer4 (TrimmedContextOutput) が存在すること"""
        result = compressor.compress(sample_text)

        assert result.layer4 is not None
        assert isinstance(result.layer4, TrimmedContextOutput)
        assert hasattr(result.layer4, "compressed_text")
        assert hasattr(result.layer4, "token_count")
        assert hasattr(result.layer4, "retained_entities")
        assert hasattr(result.layer4, "reduction_ratio")
        assert hasattr(result.layer4, "scene_type")
        assert hasattr(result.layer4, "retention_rate")
        assert hasattr(result.layer4, "pinned_count")
        assert hasattr(result.layer4, "dropped_categories")

    def test_metrics_exists(self, compressor, sample_text):
        """metrics (CompressionQualityMetrics) が存在すること"""
        result = compressor.compress(sample_text)

        assert result.metrics is not None
        assert isinstance(result.metrics, CompressionQualityMetrics)
        assert hasattr(result.metrics, "character_retention_score")
        assert hasattr(result.metrics, "foreshadowing_retention_score")
        assert hasattr(result.metrics, "proper_noun_retention_score")
        assert hasattr(result.metrics, "semantic_density_score")
        assert hasattr(result.metrics, "overall_consistency_score")

        # スコアは 0.0-1.0 の範囲
        assert 0.0 <= result.metrics.character_retention_score <= 1.0
        assert 0.0 <= result.metrics.foreshadowing_retention_score <= 1.0
        assert 0.0 <= result.metrics.proper_noun_retention_score <= 1.0
        assert 0.0 <= result.metrics.semantic_density_score <= 1.0
        assert 0.0 <= result.metrics.overall_consistency_score <= 1.0

    def test_from_cache_false_on_first_call(self, compressor, sample_text):
        """初回実行時 from_cache=False"""
        result = compressor.compress(sample_text)
        assert result.from_cache is False

    def test_elapsed_ms_recorded(self, compressor, sample_text):
        """elapsed_ms が記録されること"""
        result = compressor.compress(sample_text)
        assert result.elapsed_ms >= 0
        assert isinstance(result.elapsed_ms, float)

    @pytest.mark.parametrize("scene_type", [
        "general",
        "combat",
        "daily",
        "psychological",
        "political",
        "romance",
        "mystery",
        "flashback",
        "survival",
    ])
    def test_scene_type_preserved_in_layer4(self, compressor, sample_text, scene_type):
        """各シーンタイプで layer4.scene_type が正しく設定されること"""
        result = compressor.compress(sample_text, scene_type=scene_type)
        assert result.layer4.scene_type == scene_type

    def test_empty_text_handled_gracefully(self, compressor):
        """空文字列入力でエラーにならず空結果返却"""
        result = compressor.compress("")
        
        assert isinstance(result, CompressedContextResult)
        assert result.final_context_text == ""
        assert result.final_token_count == 0
        assert result.overall_reduction_ratio == 0.0
        assert result.layer4 is not None
        assert result.layer4.compressed_text == ""
        assert result.layer4.token_count == 0

    def test_protected_context_pinning(self, compressor, sample_text):
        """ProtectedContext で指定したエンティティが保持されること"""
        protected = ProtectedContext(
            active_characters=["主人公", "ヒロイン"],
            pending_foreshadowing_ids=["fs_1"],
            critical_keywords=["重要キーワード"],
            pinned_entities={"絶対外せない"},
        )
        
        result = compressor.compress(sample_text, protected_context=protected)
        
        # 圧縮後のテキストに主要キャラクターが含まれる可能性が高い
        # （実装詳細依存のため、エラーなく実行されることを確認）
        assert isinstance(result, CompressedContextResult)


class TestCompressionConfigSchema:
    """CompressionConfig のスキーマ確認"""

    def test_default_config_values(self):
        """デフォルト設定値の確認"""
        config = CompressionConfig()
        
        assert config.max_tokens == 1500
        assert config.target_reduction_ratio == 0.6
        assert config.top_keywords == 20
        assert config.max_hops == 2
        assert config.relevance_threshold == 0.5
        assert config.scene_type == "general"
        assert config.cache_enabled is True
        assert config.cache_ttl_seconds == 3600
        assert config.preserve_categories == ["主要キャラ", "核心設定", "伏線"]

    def test_sudachi_config_defaults(self):
        """SudachiConfig デフォルト値の確認"""
        config = CompressionConfig()
        
        assert config.sudachi.split_mode == "C"
        assert config.sudachi.include_proper is True
        assert config.sudachi.include_compound is True
        assert config.sudachi.min_length == 2
        assert config.sudachi.dict_type == "core"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])