from pydantic import BaseModel

# 1MトークンあたりのUSD単価 (2026年時点想定)
MODEL_PRICING = {
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40, "cached_input": 0.025},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00, "cached_input": 0.08},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00, "cached_input": 0.30},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "cached_input": 0.075},
}

ROUTING_TIERS = {
    "tier1_light": "gemini-2.0-flash",      # 構成・ブレスト・要約・監査
    "tier2_standard": "claude-3-5-haiku",   # 日常シーン・展開回の執筆
    "tier3_premium": "claude-3-5-sonnet",   # クライマックス・第1話・重要伏線回収
}