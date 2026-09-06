"""Integration tests for SudachiPy tokenizer in full compression pipeline."""
from __future__ import annotations

import pytest

from src.services.compression import (
    FourLayerCompressor,
    CompressionConfig,
    SudachiConfig,
)


class TestFullPipelineWithSudachi:
    """Test FourLayerCompressor with Sudachi tokenizer."""

    def test_compression_pipeline_basic(self):
        """Basic compression pipeline with Sudachi tokenizer."""
        config = CompressionConfig(max_tokens=200)
        compressor = FourLayerCompressor(config=config)

        text = "勇者アルカディアが聖剣エクスカリバーを抜いて魔王ヴォルケインを倒す。"
        entities = [
            {"id": "1", "name": "アルカディア"},
            {"id": "2", "name": "ヴォルケイン"},
        ]
        relations = [{"source": "1", "target": "2", "type": "敵対"}]

        result = compressor.compress(
            text,
            entities=entities,
            relations=relations,
            scene_type="combat",
            bypass_cache=True,
        )

        assert result.final_context_text
        assert "アルカディア" in result.final_context_text
        # エクスカリバーは抽象化されて「伝説級武装」になる
        assert "伝説級武装" in result.final_context_text or "エクスカリバー" in result.final_context_text
        assert result.layer1 is not None
        assert len(result.layer1.extracted_keywords) > 0
        assert "エクスカリバー" in result.layer1.extracted_keywords

    def test_compression_with_custom_sudachi_config(self):
        """Compression with custom SudachiConfig (min_length=3)."""
        config = CompressionConfig(
            max_tokens=200,
            sudachi=SudachiConfig(min_length=3),
        )
        compressor = FourLayerCompressor(config=config)

        text = "勇者アルカディアが聖剣エクスカリバーを抜く。"
        entities = [{"id": "1", "name": "アルカディア"}]
        relations = []

        result = compressor.compress(
            text,
            entities=entities,
            relations=relations,
            scene_type="combat",
            bypass_cache=True,
        )

        # With min_length=3, 2-char tokens like "勇者", "聖剣" should be filtered
        for kw in result.layer1.extracted_keywords:
            assert len(kw) >= 3

    def test_political_scene_entity_retention(self):
        """Political scene should retain key entities (regression test)."""
        config = CompressionConfig(max_tokens=300, cache_enabled=False)
        compressor = FourLayerCompressor(config=config)

        text = """宰相バルガスは王都グランヴァルの議会で関税引き上げを提案した。
商人ギルドと辺境警備隊は強く反発し、エルシオン協定を引き合いに出して交渉を要求した。
ミレナはバルガスと対立し、関税政策の撤回を求めて議会で演説した。"""

        entities = [
            {"id": "e1", "name": "バルガス", "labels": ["Character"]},
            {"id": "e2", "name": "ミレナ", "labels": ["Character"]},
            {"id": "e3", "name": "商人ギルド", "labels": ["Organization", "Faction"]},
            {"id": "e4", "name": "辺境警備隊", "labels": ["Organization", "Faction"]},
            {"id": "e5", "name": "エルシオン協定", "labels": ["Rule", "Lore"]},
            {"id": "e6", "name": "関税", "labels": ["Policy", "Lore"]},
        ]
        relations = [
            {"source": "e1", "target": "e2", "type": "対立"},
            {"source": "e3", "target": "e4", "type": "対立"},
            {"source": "e1", "target": "e5", "type": "引用"},
            {"source": "e2", "target": "e6", "type": "反対"},
        ]

        result = compressor.compress(
            text,
            entities=entities,
            relations=relations,
            scene_type="political",
            bypass_cache=True,
        )

        # Check key entities are retained in final context
        final_text = result.final_context_text
        assert "バルガス" in final_text
        assert "ミレナ" in final_text
        assert "エルシオン協定" in final_text or "エルシオン" in final_text
        assert "関税" in final_text

    def test_compound_proper_nouns_preserved(self):
        """Compound proper nouns like グランヴァル, エクスカリバー should be preserved."""
        config = CompressionConfig(max_tokens=300, cache_enabled=False)
        compressor = FourLayerCompressor(config=config)

        text = "王都グランヴァルで聖剣エクスカリバーを持つ勇者が魔王ヴォルケインと戦う。"
        entities = [
            {"id": "1", "name": "王都グランヴァル", "labels": ["Location"]},
            {"id": "2", "name": "聖剣エクスカリバー", "labels": ["Item"]},
            {"id": "3", "name": "ヴォルケイン", "labels": ["Character"]},
        ]
        relations = [
            {"source": "3", "target": "2", "type": "対立"},
        ]

        result = compressor.compress(
            text,
            entities=entities,
            relations=relations,
            scene_type="combat",
            bypass_cache=True,
        )

        final_text = result.final_context_text
        # Compound nouns should be preserved in layer1 keywords
        assert "グランヴァル" in result.layer1.extracted_keywords
        assert "エクスカリバー" in result.layer1.extracted_keywords
        assert "ヴォルケイン" in result.layer1.extracted_keywords
        # Final text may have abstracted forms
        assert "伝説級武装" in final_text or "エクスカリバー" in final_text

    def test_cache_works_with_sudachi(self):
        """Caching should work with Sudachi tokenizer."""
        config = CompressionConfig(max_tokens=200, cache_enabled=True)
        compressor = FourLayerCompressor(config=config)

        text = "勇者アルカディアが聖剣エクスカリバーを抜く。"
        entities = [{"id": "1", "name": "アルカディア"}]
        relations = []

        # First call - cache miss
        result1 = compressor.compress(
            text, entities=entities, relations=relations,
            scene_type="combat", bypass_cache=False,
        )
        assert result1.from_cache is False

        # Second call - cache hit
        result2 = compressor.compress(
            text, entities=entities, relations=relations,
            scene_type="combat", bypass_cache=False,
        )
        assert result2.from_cache is True
        assert result2.final_context_text == result1.final_context_text

    def test_different_scene_types(self):
        """Test all scene types work with Sudachi tokenizer."""
        config = CompressionConfig(max_tokens=200, cache_enabled=False)
        compressor = FourLayerCompressor(config=config)

        text = "勇者アルカディアが聖剣エクスカリバーで魔王ヴォルケインを倒す。"
        entities = [
            {"id": "1", "name": "アルカディア"},
            {"id": "2", "name": "ヴォルケイン"},
        ]
        relations = [{"source": "1", "target": "2", "type": "敵対"}]

        for scene_type in ["combat", "daily", "psychological", "political", "general"]:
            result = compressor.compress(
                text,
                entities=entities,
                relations=relations,
                scene_type=scene_type,
                bypass_cache=True,
            )
            assert result.final_context_text
            assert result.layer4.scene_type == scene_type


class TestTokenizerFallback:
    """Test fallback behavior when Sudachi unavailable."""

    def test_fallback_to_regex(self, monkeypatch):
        """When Sudachi fails, should fall back to regex tokenizer."""
        import src.services.compression.japanese_tokenizer as jt_module

        # Simulate Sudachi unavailable
        monkeypatch.setattr(jt_module, 'SUDACHI_AVAILABLE', False)

        from src.services.compression.japanese_tokenizer import create_japanese_tokenizer
        from src.services.compression import FourLayerCompressor, CompressionConfig

        tokenizer = create_japanese_tokenizer()
        assert type(tokenizer).__name__ == "RegexJapaneseTokenizer"

        # Compression should still work
        config = CompressionConfig(max_tokens=200)
        compressor = FourLayerCompressor(config=config)

        text = "勇者アルカディアが聖剣エクスカリバーを抜く。"
        result = compressor.compress(text, bypass_cache=True)
        assert result.final_context_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])