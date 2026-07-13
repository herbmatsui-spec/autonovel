import time
import logging
from typing import List, Dict, Any
from streamlit_app import api_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("benchmark")

def benchmark_api_call(func, *args, iterations=5, label="API Call"):
    """
    API呼び出しの応答時間を測定し、キャッシュの効果を検証する
    """
    times = []
    logger.info(f"Benchmarking {label}...")
    for i in range(iterations):
        start = time.perf_counter()
        try:
            func(*args)
        except Exception as e:
            logger.error(f"Error during iteration {i}: {e}")
        end = time.perf_counter()
        times.append(end - start)
        logger.info(f"  Iteration {i+1}: {times[-1]:.4f}s")
    
    avg_time = sum(times) / len(times)
    logger.info(f"Average time for {label}: {avg_time:.4f}s")
    return times

def run_benchmarks():
    # テスト用のダミー task_id (実際には存在するIDが必要だが、ここではAPI clientの挙動を確認)
    test_task_id = "test_task_123"
    
    # 1. get_task_status のキャッシュ性能検証
    # 初回は実リクエスト、2回目以降はキャッシュされるはず
    results = benchmark_api_call(api_client.get_task_status, test_task_id, iterations=5, label="get_task_status")
    
    if len(results) > 1:
        first_call = results[0]
        subsequent_calls = results[1:]
        avg_subsequent = sum(subsequent_calls) / len(subsequent_calls)
        improvement = (first_call - avg_subsequent) / first_call * 100
        logger.info(f"Cache Improvement: {improvement:.2f}% reduction in response time")

if __name__ == "__main__":
    run_benchmarks()
