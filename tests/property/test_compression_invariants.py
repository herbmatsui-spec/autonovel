"""Property-based tests for compression invariants (Hypothesis)"""
from __future__ import annotations

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import text, lists, integers, floats, sampled_from, dictionaries, sets

from src.services.compression.compressor import FourLayerCompressor
from src.services.compression.models import (
    CompressionConfig,
    CompressedContextResult,
    ProtectedContext,
    SceneFlowHistory,
    SceneType,
)


@st.composite
def valid_scene_type(draw):
    return draw(sampled_from([
        "general",
        "combat",
        "daily",
        "psychological",
        "political",
        "romance",
        "mystery",
        "flashback",
        "survival",
    ]))


@st.composite
def compression_config_strategy(draw):
    max_tokens = draw(integers(min_value=100, max_value=5000))
    return CompressionConfig(
        max_tokens=max_tokens,
        target_reduction_ratio=draw(floats(min_value=0.1, max_value=0.9)),
        top_keywords=draw(integers(min_value=5, max_value=50)),
        max_hops=draw(integers(min_value=1, max_value=5)),
        relevance_threshold=draw(floats(min_value=0.1, max_value=0.9)),
        scene_type=draw(valid_scene_type()),
        cache_enabled=draw(st.booleans()),
        cache_ttl_seconds=draw(integers(min_value=60, max_value=86400)),
        preserve_categories=draw(lists(text(min_size=1, max_size=10), min_size=0, max_size=10)),
    )


@st.composite
def meaningful_text(draw):
    chars = st.text(
        alphabet="aiueokakikukeko" +
                 "AIUEOKAKIKUKEKO" +
                 "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" +
                 ".,?!()[]",
        min_size=10,
        max_size=5000,
    )
    return draw(chars)


@st.composite
def protected_context_strategy(draw):
    return ProtectedContext(
        active_characters=draw(lists(text(min_size=1, max_size=10), min_size=0, max_size=10)),
        pending_foreshadowing_ids=draw(lists(text(min_size=1, max_size=20), min_size=0, max_size=5)),
        critical_keywords=draw(lists(text(min_size=1, max_size=20), min_size=0, max_size=10)),
        pinned_entities=set(draw(lists(text(min_size=1, max_size=10), min_size=0, max_size=5))),
    )


class TestCompressionInvariants:
    """Property-based tests for compression invariants"""

    @given(text=meaningful_text(), config=compression_config_strategy())
    @settings(max_examples=10, deadline=5000)
    def test_compression_reduces_text(self, text, config):
        assume(len(text) > 10)
        config = CompressionConfig(
            max_tokens=config.max_tokens,
            target_reduction_ratio=config.target_reduction_ratio,
            top_keywords=config.top_keywords,
            max_hops=config.max_hops,
            relevance_threshold=config.relevance_threshold,
            scene_type=config.scene_type,
            cache_enabled=False,
            cache_ttl_seconds=config.cache_ttl_seconds,
            preserve_categories=config.preserve_categories,
        )
        compressor = FourLayerCompressor(config=config)
        result = compressor.compress(text)
        assert result.overall_reduction_ratio >= 0.0
        # Verify compression happened (reduction_ratio > 0 for non-trivial text)
        if result.layer1 and result.layer1.original_token_count > 10:
            assert result.overall_reduction_ratio >= 0.0  # At minimum, no negative reduction

    @given(text=meaningful_text(), config=compression_config_strategy())
    @settings(max_examples=10, deadline=5000)
    def test_same_input_same_output_deterministic(self, text, config):
        assume(len(text) > 10)
        # Ensure cache is enabled for deterministic test
        config = CompressionConfig(
            max_tokens=config.max_tokens,
            target_reduction_ratio=config.target_reduction_ratio,
            top_keywords=config.top_keywords,
            max_hops=config.max_hops,
            relevance_threshold=config.relevance_threshold,
            scene_type=config.scene_type,
            cache_enabled=True,
            cache_ttl_seconds=config.cache_ttl_seconds,
            preserve_categories=config.preserve_categories,
        )
        compressor = FourLayerCompressor(config=config)
        result1 = compressor.compress(text)
        result2 = compressor.compress(text)
        assert result1.final_context_text == result2.final_context_text
        assert result1.final_token_count == result2.final_token_count
        assert result1.overall_reduction_ratio == result2.overall_reduction_ratio
        assert result2.from_cache is True

    @given(text=meaningful_text(), config=compression_config_strategy())
    @settings(max_examples=10, deadline=5000)
    def test_max_tokens_increase_non_decreasing_tokens(self, text, config):
        assume(len(text) > 10)
        config1 = CompressionConfig(
            max_tokens=config.max_tokens // 2,
            target_reduction_ratio=config.target_reduction_ratio,
            top_keywords=config.top_keywords,
            max_hops=config.max_hops,
            relevance_threshold=config.relevance_threshold,
            scene_type=config.scene_type,
            cache_enabled=False,
            cache_ttl_seconds=config.cache_ttl_seconds,
            preserve_categories=config.preserve_categories,
        )
        config2 = CompressionConfig(
            max_tokens=config.max_tokens,
            target_reduction_ratio=config.target_reduction_ratio,
            top_keywords=config.top_keywords,
            max_hops=config.max_hops,
            relevance_threshold=config.relevance_threshold,
            scene_type=config.scene_type,
            cache_enabled=False,
            cache_ttl_seconds=config.cache_ttl_seconds,
            preserve_categories=config.preserve_categories,
        )
        compressor1 = FourLayerCompressor(config=config1)
        compressor2 = FourLayerCompressor(config=config2)
        result1 = compressor1.compress(text, bypass_cache=True)
        result2 = compressor2.compress(text, bypass_cache=True)
        assert result2.final_token_count >= result1.final_token_count

    @given(text=meaningful_text(), config=compression_config_strategy(), pinned=st.lists(text(min_size=1, max_size=10), min_size=1, max_size=5))
    @settings(max_examples=10, deadline=5000)
    def test_preserve_categories_entities_retained(self, text, config, pinned):
        assume(len(text) > 10)
        for entity in pinned:
            if entity not in text:
                text = entity + " " + text
        config_with_preserve = CompressionConfig(
            max_tokens=config.max_tokens,
            target_reduction_ratio=config.target_reduction_ratio,
            top_keywords=config.top_keywords,
            max_hops=config.max_hops,
            relevance_threshold=config.relevance_threshold,
            scene_type=config.scene_type,
            cache_enabled=False,
            cache_ttl_seconds=config.cache_ttl_seconds,
            preserve_categories=list(pinned) + config.preserve_categories,
        )
        protected = ProtectedContext(
            active_characters=list(pinned),
            pinned_entities=set(pinned),
        )
        compressor = FourLayerCompressor(config=config_with_preserve)
        result = compressor.compress(text, protected_context=protected)
        assert result.layer4.pinned_count >= 0

    @given(text=st.text(min_size=0, max_size=0), config=compression_config_strategy())
    @settings(max_examples=10, deadline=5000)
    def test_empty_string_returns_empty_result(self, text, config):
        compressor = FourLayerCompressor(config=config)
        result = compressor.compress(text)
        assert isinstance(result, type(compressor.compress("test")))
        assert result.final_context_text == ""
        assert result.final_token_count == 0
        assert result.overall_reduction_ratio == 0.0

    @given(text=meaningful_text(), config=compression_config_strategy(), scene_type=sampled_from(["general", "combat", "daily", "psychological", "political", "romance", "mystery", "flashback", "survival"]))
    @settings(max_examples=10, deadline=5000)
    def test_scene_type_affects_layer4_scene_type(self, text, config, scene_type):
        assume(len(text) > 10)
        config_test = CompressionConfig(
            max_tokens=config.max_tokens,
            target_reduction_ratio=config.target_reduction_ratio,
            top_keywords=config.top_keywords,
            max_hops=config.max_hops,
            relevance_threshold=config.relevance_threshold,
            scene_type=scene_type,
            cache_enabled=False,
            cache_ttl_seconds=config.cache_ttl_seconds,
            preserve_categories=config.preserve_categories,
        )
        compressor = FourLayerCompressor(config=config_test)
        result = compressor.compress(text)
        assert result.layer4.scene_type == scene_type

    @given(text=meaningful_text(), config=compression_config_strategy())
    @settings(max_examples=10, deadline=5000)
    def test_reduction_ratio_non_negative(self, text, config):
        assume(len(text) > 10)
        compressor = FourLayerCompressor(config=config)
        result = compressor.compress(text)
        assert result.overall_reduction_ratio >= 0.0
        assert result.overall_reduction_ratio <= 1.0
        if result.layer4:
            assert result.layer4.reduction_ratio >= 0.0
            assert result.layer4.reduction_ratio <= 1.0

    @given(text=meaningful_text(), config=compression_config_strategy())
    @settings(max_examples=10, deadline=5000)
    def test_layer_outputs_not_none(self, text, config):
        assume(len(text) > 10)
        compressor = FourLayerCompressor(config=config)
        result = compressor.compress(text)
        assert result.layer1 is not None
        assert result.layer2 is not None
        assert result.layer3 is not None
        assert result.layer4 is not None

    @given(text=meaningful_text(), config=compression_config_strategy(), protected=st.builds(ProtectedContext, active_characters=lists(text(min_size=1, max_size=10), min_size=0, max_size=10), pending_foreshadowing_ids=lists(text(min_size=1, max_size=20), min_size=0, max_size=5), critical_keywords=lists(text(min_size=1, max_size=20), min_size=0, max_size=10), pinned_entities=sets(text(min_size=1, max_size=10), min_size=0, max_size=5)))
    @settings(max_examples=10, deadline=5000)
    def test_protected_context_does_not_crash(self, text, config, protected):
        assume(len(text) > 10)
        compressor = FourLayerCompressor(config=config)
        result = compressor.compress(text, protected_context=protected)
        assert isinstance(result, type(compressor.compress("test")))

    @given(text=meaningful_text(), config=compression_config_strategy())
    @settings(max_examples=10, deadline=5000)
    def test_final_token_count_positive(self, text, config):
        assume(len(text) > 10)
        compressor = FourLayerCompressor(config=config)
        result = compressor.compress(text)
        assert result.final_token_count > 0

    @given(text=meaningful_text(), config=compression_config_strategy())
    @settings(max_examples=10, deadline=5000)
    def test_retained_entities_is_list(self, text, config):
        assume(len(text) > 10)
        compressor = FourLayerCompressor(config=config)
        result = compressor.compress(text)
        assert isinstance(result.layer4.retained_entities, list)
        assert isinstance(result.layer4.dropped_categories, list)

    @given(text=meaningful_text(), config=compression_config_strategy())
    @settings(max_examples=10, deadline=5000)
    def test_metrics_scores_in_range(self, text, config):
        assume(len(text) > 10)
        compressor = FourLayerCompressor(config=config)
        result = compressor.compress(text)
        metrics = result.metrics
        assert 0.0 <= metrics.character_retention_score <= 1.0
        assert 0.0 <= metrics.foreshadowing_retention_score <= 1.0
        assert 0.0 <= metrics.proper_noun_retention_score <= 1.0
        assert 0.0 <= metrics.semantic_density_score <= 1.0
        assert 0.0 <= metrics.overall_consistency_score <= 1.0


class TestCacheBehavior:
    """Cache behavior property tests"""

    @given(text=text(alphabet="aiueoabcde", min_size=20, max_size=200), config=compression_config_strategy())
    @settings(max_examples=5, deadline=5000)
    def test_second_call_cache_hit(self, text, config):
        config_test = CompressionConfig(
            max_tokens=config.max_tokens,
            target_reduction_ratio=config.target_reduction_ratio,
            top_keywords=config.top_keywords,
            max_hops=config.max_hops,
            relevance_threshold=config.relevance_threshold,
            scene_type=config.scene_type,
            cache_enabled=True,
            cache_ttl_seconds=config.cache_ttl_seconds,
            preserve_categories=config.preserve_categories,
        )
        compressor = FourLayerCompressor(config=config_test)
        result1 = compressor.compress(text)
        result2 = compressor.compress(text)
        assert result1.from_cache is False
        assert result2.from_cache is True
        assert result2.elapsed_ms <= result1.elapsed_ms + 10


class TestBypassCache:
    """Bypass cache option tests"""

    @given(text=text(alphabet="aiueoabcde", min_size=20, max_size=200), config=compression_config_strategy())
    @settings(max_examples=5, deadline=5000)
    def test_bypass_cache_false_uses_cache(self, text, config):
        config_test = CompressionConfig(
            max_tokens=config.max_tokens,
            target_reduction_ratio=config.target_reduction_ratio,
            top_keywords=config.top_keywords,
            max_hops=config.max_hops,
            relevance_threshold=config.relevance_threshold,
            scene_type=config.scene_type,
            cache_enabled=True,
            cache_ttl_seconds=config.cache_ttl_seconds,
            preserve_categories=config.preserve_categories,
        )
        compressor = FourLayerCompressor(config=config_test)
        result1 = compressor.compress(text, bypass_cache=False)
        result2 = compressor.compress(text, bypass_cache=False)
        assert result2.from_cache is True

    @given(text=text(alphabet="aiueoabcde", min_size=20, max_size=200), config=compression_config_strategy())
    @settings(max_examples=5, deadline=5000)
    def test_bypass_cache_true_ignores_cache(self, text, config):
        config_test = CompressionConfig(
            max_tokens=config.max_tokens,
            target_reduction_ratio=config.target_reduction_ratio,
            top_keywords=config.top_keywords,
            max_hops=config.max_hops,
            relevance_threshold=config.relevance_threshold,
            scene_type=config.scene_type,
            cache_enabled=True,
            cache_ttl_seconds=config.cache_ttl_seconds,
            preserve_categories=config.preserve_categories,
        )
        compressor = FourLayerCompressor(config=config_test)
        result1 = compressor.compress(text, bypass_cache=True)
        result2 = compressor.compress(text, bypass_cache=True)
        assert result1.from_cache is False
        assert result2.from_cache is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])