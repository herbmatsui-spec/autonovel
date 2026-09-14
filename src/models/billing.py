from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class PlanTier(str, Enum):
    FREE = "free"
    STARTER = "starter"      # JPY 980 / 月 (300クレジット)
    PRO = "pro"              # JPY 2,980 / 月 (1,200クレジット)
    ENTERPRISE = "enterprise"# JPY 9,800 / 月 (5,000クレジット)

class TransactionType(str, Enum):
    MONTHLY_GRANT = "monthly_grant"  # サブスク月次付与
    PACK_PURCHASE = "pack_purchase"  # 都度クレジット購入
    CONSUMPTION = "consumption"      # 生成による消費
    REFUND = "refund"                # 失敗による返還
    ADMIN_ADJUST = "admin_adjust"    # 運営付与

class CreateCheckoutRequest(BaseModel):
    price_id: str = Field(..., description="Stripe Price ID")
    mode: str = Field("subscription", pattern="^(subscription|payment)$")

class CheckoutResponse(BaseModel):
    checkout_url: str

class CreditBalanceResponse(BaseModel):
    balance: int
    plan_tier: PlanTier
    current_period_end: datetime | None = None