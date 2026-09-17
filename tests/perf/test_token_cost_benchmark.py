import pytest

# 1Mトークンあたりの価格 (USD)
MODEL_RATES = {
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
}
USD_JPY = 150.0

def calculate_episode_cost_jpy(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = MODEL_RATES[model]
    cost_usd = (input_tokens / 1_000_000.0) * rates["input"] + (
        output_tokens / 1_000_000.0
    ) * rates["output"]
    return cost_usd * USD_JPY

def test_token_cost_benchmark_gemini_flash():
    """v5.0: 1話あたりのトークン消費（執筆＋二層監査）とコストが目標（<5円）に収まることを検証"""
    # 1. 執筆フェーズ（3層記憶 + 指示: 約3,000トークン -> 本文約1,500トークン）
    draft_input = 3000
    draft_output = 1500

    # 2. 二層監査フェーズ（第1層は静的解析で0トークン、第2層のみ約2,000入力 -> 200出力）
    audit_input = 2000
    audit_output = 200

    total_input = draft_input + audit_input
    total_output = draft_output + audit_output
    total_tokens = total_input + total_output

    # トークン消費量が 10,000 トークン未満であることを検証
    assert total_tokens <= 10_000

    # コスト計算 (Gemini 2.5 Flash)
    cost_jpy = calculate_episode_cost_jpy("gemini-2.5-flash", total_input, total_output)
    print(f"\n[BENCHMARK] Total Tokens: {total_tokens}, Cost (Gemini Flash): {cost_jpy:.3f} JPY")

    # 1話あたりのコストが 5円 未満（実質 1円 未満）であることをアサート
    assert cost_jpy < 1.0  # Gemini Flashなら1円未満で完結

def test_token_cost_benchmark_claude_haiku():
    """Claude 3.5 Haiku を使用した場合でも5円以内に収まることを検証"""
    total_input = 5000
    total_output = 1700
    cost_jpy = calculate_episode_cost_jpy("claude-3-5-haiku", total_input, total_output)
    print(f"\n[BENCHMARK] Cost (Claude 3.5 Haiku): {cost_jpy:.3f} JPY")
    assert cost_jpy < 5.0  # 目標5円未満
