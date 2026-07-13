import os
import time

from prompts.registry import PromptRegistry


def test_prompt_registry_performance():
    """キャッシュの有無によるパフォーマンス（実行時間）の差を計測する"""
    test_dir = os.path.abspath("tests/prompts/perf_test")
    os.makedirs(test_dir, exist_ok=True)
    template_path = os.path.join(test_dir, "perf_test.j2")

    with open(template_path, "w", encoding="utf-8") as f:
        f.write("---\nversion: 1.0\n---\nHello {{ name }}! This is a performance test template. " * 10)

    registry = PromptRegistry(templates_dir=test_dir)
    context = {"name": "Zoo"}
    iterations = 1000

    # 1. キャッシュなし（初回読み込み）
    start_time = time.perf_counter()
    registry._get_template_source_sync("perf_test.j2")
    end_time = time.perf_counter()
    first_load_time = end_time - start_time

    # 2. キャッシュあり（2回目以降）
    start_time = time.perf_counter()
    for _ in range(iterations):
        registry._get_template_source_sync("perf_test.j2")
    end_time = time.perf_counter()
    cached_load_time = (end_time - start_time) / iterations

    print(f"\nFirst load time: {first_load_time:.6f}s")
    print(f"Average cached load time: {cached_load_time:.6f}s")
    print(f"Speedup: {first_load_time / cached_load_time:.2f}x")

    assert cached_load_time < first_load_time
