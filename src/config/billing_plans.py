PLAN_CONFIG = {
    "free": {"price_jpy": 0, "monthly_credits": 50, "max_parallel_jobs": 1},
    "starter": {"price_jpy": 980, "monthly_credits": 300, "max_parallel_jobs": 2},
    "pro": {"price_jpy": 2980, "monthly_credits": 1200, "max_parallel_jobs": 4},
    "enterprise": {"price_jpy": 9800, "monthly_credits": 5000, "max_parallel_jobs": 10},
}

# Stripe Price ID とプラン・付与クレジットのマッピング
STRIPE_PRICE_TO_PLAN = {
    "price_free": {"tier": "free", "monthly_credits": 0},
    "price_starter": {"tier": "starter", "monthly_credits": 300},
    "price_pro": {"tier": "pro", "monthly_credits": 1200},
    "price_enterprise": {"tier": "enterprise", "monthly_credits": 5000},
}

def get_credits_for_price_id(price_id: str) -> int:
    """Stripe Price IDから付与すべき月次クレジット数を取得する。"""
    if price_id in STRIPE_PRICE_TO_PLAN:
        return STRIPE_PRICE_TO_PLAN[price_id]["monthly_credits"]
    # キーが直接プラン名 (starter, pro, enterprise) の場合
    if price_id in PLAN_CONFIG:
        return PLAN_CONFIG[price_id]["monthly_credits"]
    return 0

def get_tier_for_price_id(price_id: str) -> str:
    """Stripe Price IDからPlan Tier (free, starter, pro, enterprise) を取得する。"""
    if price_id in STRIPE_PRICE_TO_PLAN:
        return STRIPE_PRICE_TO_PLAN[price_id]["tier"]
    if price_id in PLAN_CONFIG:
        return price_id
    return "free"

# 1クレジット ≒ 約 2.5〜3 円相当
TASK_CREDIT_COSTS = {
    "plot_expansion": 2,       # プロット構成・ブレスト (Gemini Flash)
    "writing_standard": 10,    # 1エピソード本文執筆 (約3,000字 / Haiku or mini)
    "writing_climax_pro": 25,  # クライマックス最高品質執筆 (Claude 3.5 Sonnet)
    "audit_full": 5,           # 8オーディター並列監査
    "illustration_generate": 8,# 挿絵1枚生成 (SDXL / Imagen)
    "voice_synthesize": 6,     # VOICEVOX章音声合成
}