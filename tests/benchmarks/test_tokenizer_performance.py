"""Performance benchmarks for Japanese tokenizers."""
from __future__ import annotations

import pytest
import time
import statistics

from src.services.compression.japanese_tokenizer import (
    create_japanese_tokenizer,
    SudachiTokenizer,
    RegexJapaneseTokenizer,
    HybridJapaneseTokenizer,
    SudachiConfig,
    SUDACHI_AVAILABLE,
)


# Test texts of varying lengths
SHORT_TEXT = "勇者アルカディアが聖剣エクスカリバーを抜く。"

MEDIUM_TEXT = """勇者アルカディアは王都グランヴァルを揺るがす経済制裁の報せを受け取った。
宰相バルガスが画策する不当な関税引き上げにより、辺境の領民は飢えに瀕している。
アルカディアは王宮地下深くに眠る伝説級武装、聖剣エクスカリバーの封印を解くため旅立った。"""

LONG_TEXT = MEDIUM_TEXT * 10  # ~3000 chars


class TestTokenizerPerformance:
    """Performance benchmarks for tokenizers."""

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_sudachi_tokenizer_latency(self):
        """SudachiTokenizer should process text within acceptable latency."""
        tokenizer = SudachiTokenizer(SudachiConfig())
        
        # Warmup
        for _ in range(3):
            tokenizer.extract_nouns(MEDIUM_TEXT)
        
        # Benchmark
        iterations = 10
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            tokenizer.extract_nouns(MEDIUM_TEXT)
            latencies.append((time.perf_counter() - start) * 1000)  # ms
        
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]
        
        print(f"\nSudachiTokenizer (medium text ~300 chars):")
        print(f"  Avg: {avg_latency:.1f}ms, P95: {p95_latency:.1f}ms")
        print(f"  Min: {min(latencies):.1f}ms, Max: {max(latencies):.1f}ms")
        
        # Should complete within 200ms for medium text
        assert avg_latency < 200, f"Average latency {avg_latency:.1f}ms exceeds 200ms"
        assert p95_latency < 300, f"P95 latency {p95_latency:.1f}ms exceeds 300ms"

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_sudachi_initialization_time(self):
        """SudachiTokenizer initialization should be reasonably fast."""
        start = time.perf_counter()
        tokenizer = SudachiTokenizer(SudachiConfig())
        init_time = (time.perf_counter() - start) * 1000
        
        print(f"\nSudachiTokenizer initialization: {init_time:.1f}ms")
        assert init_time < 2000, f"Initialization {init_time:.1f}ms exceeds 2s"

    def test_regex_tokenizer_latency(self):
        """RegexJapaneseTokenizer latency baseline."""
        tokenizer = RegexJapaneseTokenizer()
        
        # Warmup
        for _ in range(3):
            tokenizer.extract_nouns(MEDIUM_TEXT)
        
        # Benchmark
        iterations = 10
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            tokenizer.extract_nouns(MEDIUM_TEXT)
            latencies.append((time.perf_counter() - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        print(f"\nRegexJapaneseTokenizer (medium text):")
        print(f"  Avg: {avg_latency:.1f}ms")
        
        # Regex should be very fast
        assert avg_latency < 10, f"Regex latency {avg_latency:.1f}ms exceeds 10ms"

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_hybrid_tokenizer_latency(self):
        """HybridJapaneseTokenizer latency."""
        tokenizer = HybridJapaneseTokenizer(SudachiConfig())
        
        # Warmup
        for _ in range(3):
            tokenizer.extract_nouns(MEDIUM_TEXT)
        
        # Benchmark
        iterations = 10
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            tokenizer.extract_nouns(MEDIUM_TEXT)
            latencies.append((time.perf_counter() - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        p95_latency = sorted(latencies)[int(iterations * 0.95)]
        
        print(f"\nHybridJapaneseTokenizer (medium text):")
        print(f"  Avg: {avg_latency:.1f}ms, P95: {p95_latency:.1f}ms")
        
        # Hybrid should be slower than pure Sudachi but still reasonable
        assert avg_latency < 300, f"Hybrid avg latency {avg_latency:.1f}ms exceeds 300ms"

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_long_text_performance(self):
        """Test performance with longer text."""
        tokenizer = HybridJapaneseTokenizer(SudachiConfig())
        
        # Warmup
        tokenizer.extract_nouns(LONG_TEXT)
        
        # Benchmark
        iterations = 5
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            tokenizer.extract_nouns(LONG_TEXT)
            latencies.append((time.perf_counter() - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        print(f"\nHybridJapaneseTokenizer (long text ~3000 chars):")
        print(f"  Avg: {avg_latency:.1f}ms")
        
        # Should scale roughly linearly
        assert avg_latency < 1000, f"Long text latency {avg_latency:.1f}ms exceeds 1s"

    def test_factory_creation_performance(self):
        """Test tokenizer factory creation time."""
        start = time.perf_counter()
        tokenizer = create_japanese_tokenizer()
        creation_time = (time.perf_counter() - start) * 1000
        
        print(f"\nFactory creation time: {creation_time:.1f}ms")
        assert creation_time < 500, f"Factory creation {creation_time:.1f}ms exceeds 500ms"


class TestCompressionPipelinePerformance:
    """Performance benchmarks for full compression pipeline."""

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_full_pipeline_latency(self):
        """Full 4-layer compression pipeline latency."""
        from src.services.compression import FourLayerCompressor, CompressionConfig
        
        config = CompressionConfig(max_tokens=1500)
        compressor = FourLayerCompressor(config=config)
        
        text = LONG_TEXT
        entities = [
            {"id": "1", "name": "アルカディア"},
            {"id": "2", "name": "バルガス"},
            {"id": "3", "name": "ヴォルケイン"},
        ]
        relations = [
            {"source": "1", "target": "2", "type": "対立"},
            {"source": "1", "target": "3", "type": "敵対"},
        ]
        
        # Warmup (cache disabled)
        compressor.compress(text, entities=entities, relations=relations, 
                           scene_type="combat", bypass_cache=True)
        
        # Benchmark
        iterations = 5
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            compressor.compress(text, entities=entities, relations=relations,
                               scene_type="combat", bypass_cache=True)
            latencies.append((time.perf_counter() - start) * 1000)
        
        avg_latency = statistics.mean(latencies)
        print(f"\nFourLayerCompressor full pipeline (long text):")
        print(f"  Avg: {avg_latency:.1f}ms")
        
        # Full pipeline should complete within reasonable time
        assert avg_latency < 2000, f"Pipeline latency {avg_latency:.1f}ms exceeds 2s"

    @pytest.mark.skipif(not SUDACHI_AVAILABLE, reason="sudachipy not installed")
    def test_cache_performance(self):
        """Test cache hit vs miss performance."""
        from src.services.compression import FourLayerCompressor, CompressionConfig
        
        config = CompressionConfig(max_tokens=1500, cache_enabled=True)
        compressor = FourLayerCompressor(config=config)
        
        text = MEDIUM_TEXT
        entities = [{"id": "1", "name": "アルカディア"}]
        relations = []
        
        # First call - cache miss
        start = time.perf_counter()
        result1 = compressor.compress(text, entities=entities, relations=relations,
                                     scene_type="combat", bypass_cache=False)
        miss_time = (time.perf_counter() - start) * 1000
        
        # Second call - cache hit
        start = time.perf_counter()
        result2 = compressor.compress(text, entities=entities, relations=relations,
                                     scene_type="combat", bypass_cache=False)
        hit_time = (time.perf_counter() - start) * 1000
        
        print(f"\nCache performance:")
        print(f"  Miss: {miss_time:.1f}ms")
        print(f"  Hit:  {hit_time:.1f}ms")
        print(f"  Speedup: {miss_time/hit_time:.1f}x")
        
        # Cache hit should be significantly faster
        assert hit_time < miss_time * 0.5, "Cache hit not significantly faster"
        assert result2.from_cache is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])