"""
ベンチマークスクリプト - トークン消費・生成速度を測定
"""

import json
import time
import random
import string
from datetime import datetime

def estimate_token_count_japanese(text):
    """
    日本語テキストのトークン数を概算
    簡易ルール: 1トークン ≈ 0.5-1文字（日本語では1文字が1トークンに近い）
    ここでは 1トークン = 0.75文字 とする
    """
    if not text:
        return 0
    return len(text) / 0.75

def estimate_token_count_english(text):
    """
    英語テキストのトークン数を概算
    簡易ルール: 1トークン ≈ 0.75単語
    """
    if not text:
        return 0
    words = len(text.split())
    return words / 0.75

def generate_mock_story(genre, length_chars):
    """
    モックストーリーを生成（実際のベンチマークでは、ここで実際の生成APIを呼び出す）
    """
    # 簡易的なストーリーを生成
    templates = {
        'ファンタジー': "古代の王国で、若き勇者は伝説の剣を求めて旅に出た。途中で魔物と戦い、仲間を得ながら目的の場所に到着した。",
        'ラブコメ': "高校に転入した主人公は、クラスの人気者と偶然出会い。誤解とすれ違いを繰り返しながら、次第に惹かれ合っていく。",
        'SF': "22世紀の宇宙開発時代、主人公は新惑星の調査隊に選抜される。未知の生命体との遭遇と、船内の陰謀が待っていた。",
        'ミステリー': "静かな田舎町で起こった連続殺人事件。探偵は証拠を集め、容疑者の証言を丁寧に分析して真相に迫る。",
        '歴史': "江戸時代末期、維新志士として生きる主人公は、新しい時代への変革を願いながら日々を過ごした。"
    }
    
    base_story = templates.get(genre, "これはサンプルストーリーです。")
    # 必要な長さになるまで繰り返す
    repeated = (base_story * ((length_chars // len(base_story)) + 1))[:length_chars]
    return repeated

def run_benchmark():
    """ベンチマークを実行"""
    # 標準プロンプトセット
    test_cases = [
        {"genre": "ファンタジー", "length": 500, "description": "短編ファンタジー"},
        {"genre": "ラブコメ", "length": 1000, "description": "中編ラブコメ"},
        {"genre": "SF", "length": 2000, "description": "長編SF"},
        {"genre": "ミステリー", "length": 1500, "description": "中編ミステリー"},
        {"genre": "歴史", "length": 800, "description": "短編歴史"},
    ]
    
    results = []
    
    for case in test_cases:
        genre = case["genre"]
        length = case["length"]
        description = case["description"]
        
        logger.info(f"ベンチマーク開始: {description}")
        
        # 開始時間を記録
        start_time = time.time()
        
        # ストーリーを生成（ここではモックを使用）
        story = generate_mock_story(genre, length)
        
        # 終了時間を記録
        end_time = time.time()
        
        # 処理時間を計算
        elapsed_time = end_time - start_time
        
        # トークン消費量を概算（日本語として扱う）
        token_count = estimate_token_count_japanese(story)
        
        # 結果を記録
        result = {
            "test_case": description,
            "genre": genre,
            "requested_length_chars": length,
            "actual_length_chars": len(story),
            "estimated_token_count": round(token_count, 2),
            "generation_time_seconds": round(elapsed_time, 4),
            "tokens_per_second": round(token_count / elapsed_time, 2) if elapsed_time > 0 else 0,
            "chars_per_second": round(len(story) / elapsed_time, 2) if elapsed_time > 0 else 0
        }
        results.append(result)
        
        logger.info(f"ベンチマーク完了: {description} - {elapsed_time:.2f}秒, {token_count:.0f}トークン")
    
    # 全体のサマリーを計算
    total_time = sum(r["generation_time_seconds"] for r in results)
    total_tokens = sum(r["estimated_token_count"] for r in results)
    
    summary = {
        "benchmark_timestamp": datetime.now().isoformat(),
        "total_test_cases": len(test_cases),
        "total_generation_time_seconds": round(total_time, 4),
        "total_estimated_tokens": round(total_tokens, 2),
        "average_time_per_test": round(total_time / len(test_cases), 4) if test_cases else 0,
        "average_tokens_per_test": round(total_tokens / len(test_cases), 2) if test_cases else 0,
        "results": results
    }
    
    return summary

if __name__ == "__main__":
    # ロガーの設定（簡易版）
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    print("ベンチマークを開始します...")
    results = run_benchmark()
    
    # 結果をJSONファイルに出力
    output_file = f"scripts/benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"ベンチマーク結果を {output_file} に保存しました。")
    print(json.dumps(results, ensure_ascii=False, indent=2))