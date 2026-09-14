PLAN_CONFIG = {
    "free": {"price_jpy": 0, "monthly_credits": 50, "max_parallel_jobs": 1},
    "starter": {"price_jpy": 980, "monthly_credits": 300, "max_parallel_jobs": 2},
    "pro": {"price_jpy": 2980, "monthly_credits": 1200, "max_parallel_jobs": 4},
    "enterprise": {"price_jpy": 9800, "monthly_credits": 5000, "max_parallel_jobs": 10},
}

# 1クレジット ≒ 約 2.5〜3 円相当
TASK_CREDIT_COSTS = {
    "plot_expansion": 2,       # プロット構成・ブレスト (Gemini Flash)
    "writing_standard": 10,    # 1エピソード本文執筆 (約3,000字 / Haiku or mini)
    "writing_climax_pro": 25,  # クライマックス最高品質執筆 (Claude 3.5 Sonnet)
    "audit_full": 5,           # 8オーディター並列監査
    "illustration_generate": 8,# 挿絵1枚生成 (SDXL / Imagen)
    "voice_synthesize": 6,     # VOICEVOX章音声合成
}