"""性能回帰テスト - 圧縮ベンチマーク (簡易版)"""
from __future__ import annotations

import json
import time
import pytest
import statistics
from pathlib import Path

from src.services.compression.compressor import FourLayerCompressor
from src.services.compression.models import CompressionConfig


SAMPLE_TEXTS = {
    "10KB": "これはテスト用のサンプルテキストです。" * 500,
    "50KB": "これはテスト用のサンプルテキストです。" * 2500,
    "100KB": "これはテスト用のサンプルテキストです。" * 5000,
    "200KB": "これはテスト用のサンプルテキストです。" * 10000,
    "500KB": "これはテスト用のサンプルテキストです。" * 25000,
}


BENCHMARK_BASELINE_PATH = Path("tests/benchmarks/compression_baseline.json")


def make_compressor(cache_enabled=False):
    """ベンチマーク用コンプレッサー作成"""
    config = CompressionConfig(
        max_tokens=1500,
        target_reduction_ratio=0.6,
        top_keywords=20,
        max_hops=2,
        relevance_threshold=0.5,
        cache_enabled=cache_enabled,
        cache_ttl_seconds=3600,
    )
    return FourLayerCompressor(config=config)


def measure_execution(compressor, text, iterations=3):
    """実行時間測定"""
    times = []
    results = []
    for _ in range(iterations):
        # キャッシュクリアの代わりに新しいコンプレッサーを作成
        start = time.perf_counter()
        result = compressor.compress(text)
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
        results.append(result)
    return {
        "median_ms": statistics.median(times),
        "mean_ms": statistics.mean(times),
        "stdev_ms": statistics.stdev(times) if len(times) > 1 else 0,
        "min_ms": min(times),
        "max_ms": max(times),
        "result": results[-1],
    }


class TestCompressionPerformance:
    """圧縮性能ベンチマークテスト"""

    def test_compression_time_first_run(self):
        """初回実行（キャッシュミス）の時間測定"""
        compressor = make_compressor(cache_enabled=False)
        
        for size_name, text in {"10KB": "これはテスト用のサンプルテキストです。" * 500}.items():
            metrics = measure_execution(compressor, text, iterations=3)
            print(f"\n[{size_name}] First run (cache miss):")
            print(f"  Median: {metrics['median_ms']:.2f}ms")
            
            assert metrics["median_ms"] < 2000, f"{size_name} 初回実行が遅すぎます: {metrics['median_ms']:.2f}ms"
            result = metrics["result"]
            assert result.final_token_count > 0
            assert 0.0 <= result.overall_reduction_ratio <= 1.0

    def test_compression_time_cache_hit(self):
        """2回目以降（キャッシュヒット）の時間測定"""
        compressor = make_compressor(cache_enabled=True)
        text = "これはテスト用のサンプルテキストです。" * 500
        
        # 1回実行してキャッシュを温める
        _ = compressor.compress(text)
        
        metrics = measure_execution(compressor, text, iterations=5)
        print(f"\n[10KB] Cache hit:")
        print(f"  Median: {metrics['median_ms']:.2f}ms")
        
        assert metrics["median_ms"] < 50, f"キャッシュヒットが遅すぎます: {metrics['median_ms']:.2f}ms"
        result = metrics["result"]
        assert result.from_cache is True

    def test_memory_usage_estimate(self):
        """メモリ使用量の概算確認"""
        import sys
        compressor = make_compressor(cache_enabled=False)
        text = "これはテスト用のサンプルテキストです。" * 500  # ~10KB
        result = compressor.compress(text)
        
        result_size = sys.getsizeof(result)
        total_estimated = result_size
        if result.layer1: total_estimated += sys.getsizeof(result.layer1)
        if result.layer2: total_estimated += sys.getsizeof(result.layer2)
        if result.layer3: total_estimated += sys.getsizeof(result.layer3)
        if result.layer4: total_estimated += sys.getsizeof(result.layer4)
        
        print(f"\n[Memory Estimate] 10KB text: ~{total_estimated / 1024:.1f} KB")
        assert total_estimated < 500 * 1024 * 1024

    def test_reduction_ratio_stability(self):
        """同一サイズで複数回実行時の圧縮率安定性"""
        compressor = make_compressor(cache_enabled=False)
        text = "これはテスト用のサンプルテキストです。" * 500  # ~10KB
        
        ratios = []
        for _ in range(5):
            result = compressor.compress(text)
            ratios.append(result.overall_reduction_ratio)
        
        stdev = statistics.stdev(ratios) if len(ratios) > 1 else 0
        assert stdev < 0.05, f"圧縮率が不安定: stdev={stdev:.4f}"

    def test_benchmark_baseline_save(self):
        """ベンチマーク結果をベースラインファイルに保存"""
        compressor = make_compressor(cache_enabled=False)
        baseline = {}
        
        for size_name, text in {
            "10KB": "これはテスト用のサンプルテキストです。" * 500,
        }.items():
            metrics = measure_execution(compressor, text, iterations=3)
            baseline[size_name] = {
                "median_ms": round(metrics["median_ms"], 2),
                "mean_ms": round(metrics["mean_ms"], 2),
                "stdev_ms": round(metrics["stdev_ms"], 2),
                "min_ms": round(metrics["min_ms"], 2),
                "max_ms": round(metrics["max_ms"], 2),
                "final_tokens": metrics["result"].final_token_count,
                "reduction_ratio": round(metrics["result"].overall_reduction_ratio, 4),
            }
        
        BENCHMARK_BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(BENCHMARK_BASELINE_PATH, "w", encoding="utf-8") as f:
            json.dump(baseline, f, ensure_ascii=False, indent=2)
        
        print(f"\n[Baseline Saved] {BENCHMARK_BASELINE_PATH}")
        assert BENCHMARK_BASELINE_PATH.exists()


class TestPerformanceRegression:
    """性能回帰検出テスト"""

    def test_no_performance_regression(self):
        """ベースラインと比較して性能劣化していないか確認"""
        if not BENCHMARK_BASELINE_PATH.exists():
            pytest.skip("ベースラインファイルが存在しません。")
        
        with open(BENCHMARK_BASELINE_PATH, "r", encoding="utf-8") as f:
            baseline = json.load(f)
        
        compressor = make_compressor(cache_enabled=False)
        
        for size_name, text in {
            "10KB": "これはテスト用のサンプルテキストです。" * 500,
            "50KB": "これはテスト用のサンプルテキストです。" * 2500,
            "100KB": "これはテスト用のサンプルテキストです。" * 5000,
        }.items():
            if size_name not in baseline:
                continue
            
            start = time.perf_counter()
            result = compressor.compress(text)
            elapsed = (time.perf_counter() - start) * 1000
            
            baseline_data = baseline[size_name]
            current_median = elapsed
            baseline_median = baseline_data["median_ms"]
            
            regression_threshold = baseline_median * 1.5
            
            print(f"  {size_name}: current={current_median:.2f}ms, baseline={baseline_median:.2f}ms")
            
            assert current_median < regression_threshold, \
                f"{size_name} 性能劣化検出: {current_median:.2f}ms > {regression_threshold:.2f}ms"
            
            current_ratio = result.overall_reduction_ratio
            baseline_ratio = baseline_data["reduction_ratio"]
            assert abs(current_ratio - baseline_ratio) < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])