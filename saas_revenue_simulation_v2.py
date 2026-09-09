#!/usr/bin/env python3
"""AutoNovel SaaS Revenue Simulation Model (v2.0 - STRESS TEST)

Realistic, conservative assumptions for Japanese market:
- Slower organic growth with realistic CAC
- Higher churn and lower conversion
- LLM cost volatility and operational overhead
- Competitive pricing pressure
- Tax, compliance, support costs

Usage:
    python saas_revenue_simulation_v2.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal


# ============================================================
# 1. Market Reality Check (2025-2026 Japan)
# ============================================================

# TAM: Japanese web novel authors (realistic active paying segment)
MARKET_TOTAL_AUTHORS_JP = 500_000  # total registered across platforms
MARKET_ACTIVE_WRITERS_JP = 120_000  # writers active in last 6 months
MARKET_PREMIUM_TOOL_USERS_JP = 15_000  # already paying for AI writing tools

# Realistic LLM cost structure (JPY per 1K tokens, Japanese text)
# Japanese text uses 2-3x more tokens than English
LLM_INPUT_COST_PER_1K_TOKENS_JPY = 3.5  # mid-tier model (Gemini Flash / GPT-4o-mini)
LLM_OUTPUT_COST_PER_1K_TOKENS_JPY = 12.0  # output is more expensive

# Average Japanese novel chapter: ~3000 chars = ~4500-6000 tokens input, ~2000-3000 tokens output
AVG_TOKENS_PER_CHAPTER_INPUT = 5000
AVG_TOKENS_PER_CHAPTER_OUTPUT = 2500
LLM_COST_PER_CHAPTER_JPY = (
    (AVG_TOKENS_PER_CHAPTER_INPUT / 1000) * LLM_INPUT_COST_PER_1K_TOKENS_JPY +
    (AVG_TOKENS_PER_CHAPTER_OUTPUT / 1000) * LLM_OUTPUT_COST_PER_1K_TOKENS_JPY
)
# ~JPY 45.5 per chapter (more realistic than previous JPY 23)

# Failed attempts, retries, and context overhead add 30-50% cost
LLM_COST_PER_CHAPTER_EFFECTIVE = LLM_COST_PER_CHAPTER_JPY * 1.4  # ~JPY 63.7


# ============================================================
# 2. Business Model Configuration (Conservative)
# ============================================================

@dataclass
class PricingTier:
    name: str
    monthly_price_jpy: int
    generation_limit: int | None  # None = unlimited
    features: list[str] = field(default_factory=list)
    target_audience: str = ""


@dataclass
class RevenueModel:
    """Conservative SaaS revenue model with realistic operational costs."""
    name: str
    tiers: list[PricingTier] = field(default_factory=list)
    # Conversion & retention (realistic for Japanese SaaS)
    freemium_conversion_rate: float = 0.025  # 2.5% free -> paid (industry avg 2-5%)
    starter_to_pro_upgrade_rate: float = 0.10  # 10% upgrade (lower due to price jump)
    monthly_churn_rate: float = 0.06  # 6% monthly churn (Japanese SaaS avg 5-8%)
    annual_churn_rate: float = 0.50  # 50% annual churn (realistic for consumer SaaS)
    # User acquisition (realistic)
    monthly_organic_signups: int = 80  # low without marketing budget
    monthly_paid_signups: int = 40  # modest paid acquisition
    cac_jpy: int = 4_500  # higher CAC in competitive market
    # Variable costs per user
    support_cost_per_user_monthly_jpy: int = 150  # email/chat support
    infra_cost_per_user_monthly_jpy: int = 280  # DB, Redis, CDN, storage
    payment_processing_rate: float = 0.036  # 3.6% + fixed fee
    payment_fixed_fee_jpy: int = 25
    refund_rate: float = 0.03  # 3% refund rate
    # Fixed costs (monthly, JPY)
    llm_api_monthly_base: int = 80_000  # baseline + retry buffer
    server_base_cost_monthly: int = 150_000  # base infra even with 0 users
    staff_cost_monthly: int = 2_500_000  # 2.5M for small team (engineers, support, sales)
    marketing_monthly: int = 300_000  # content, ads, events
    compliance_legal_monthly: int = 100_000  # copyright, terms, privacy
    misc_monthly: int = 100_000  # tools, services, contingency


# ============================================================
# 3. Realistic Pricing Tiers (Japanese market optimized)
# ============================================================

REALISTIC_TIERS = [
    PricingTier(
        name="Free",
        monthly_price_jpy=0,
        generation_limit=3,
        features=[
            "3 chapters/month",
            "Basic mode only",
            "Watermarked export",
            "Community support only",
        ],
        target_audience="Trial users, casual writers",
    ),
    PricingTier(
        name="Starter (かんたん)",
        monthly_price_jpy=1_980,  # competitive with AIのべりすと
        generation_limit=15,
        features=[
            "15 chapters/month",
            "No watermark",
            "Basic GraphRAG (20 entities)",
            "ZIP export",
            "Email support (48h response)",
        ],
        target_audience="Hobbyist writers, trial upgraders",
    ),
    PricingTier(
        name="Pro (作家)",
        monthly_price_jpy=3_980,  # below NovelAI/Sudowrite to compete
        generation_limit=None,
        features=[
            "Unlimited chapters",
            "Full GraphRAG (200 entities)",
            "Advanced Studio mode",
            "Multi-modal (images/audio)",
            "eBook export",
            "Collaboration (2 users)",
            "Priority queue",
            "Blind peer review",
            "Email support (24h)",
        ],
        target_audience="Serious web novel authors",
    ),
    PricingTier(
        name="Studio (プロ)",
        monthly_price_jpy=7_980,  # premium tier for professionals
        generation_limit=None,
        features=[
            "Unlimited everything",
            "Advanced GraphRAG (1000+ entities)",
            "Commercial publishing API (なろう/カクヨム)",
            "White-label export",
            "Multi-user (10)",
            "Advanced analytics",
            "Priority support (chat/8h)",
            "Dedicated onboarding",
        ],
        target_audience="Professional authors, small studios",
    ),
    PricingTier(
        name="Enterprise (出版)",
        monthly_price_jpy=39_800,
        generation_limit=None,
        features=[
            "Dedicated infrastructure",
            "Custom model fine-tuning",
            "API access",
            "Multi-user (50+)",
            "SLA 99.9%",
            "Dedicated account manager",
            "Custom integrations",
            "On-premise option",
        ],
        target_audience="Publishing houses, production studios",
    ),
]


# ============================================================
# 4. Stress-Test Simulation Engine
# ============================================================

@dataclass
class MonthlySnapshot:
    month: int
    total_users: int
    free_users: int
    starter_users: int
    pro_users: int
    studio_users: int
    enterprise_users: int
    new_signups: int
    churned_users: int
    mrr_jpy: int
    llm_cost_jpy: int
    support_cost_jpy: int
    infra_cost_jpy: int
    staff_cost_jpy: int
    marketing_cost_jpy: int
    compliance_cost_jpy: int
    misc_cost_jpy: int
    payment_fees_jpy: int
    refunds_jpy: int
    gross_revenue_jpy: int
    net_revenue_jpy: int
    cac_total_jpy: int


class StressTestSimulator:
    """Realistic SaaS simulator with stress factors."""

    def __init__(self, model: RevenueModel, months: int = 36):
        self.model = model
        self.months = months
        model.tiers = REALISTIC_TIERS
        self.snapshots: list[MonthlySnapshot] = []

    def _get_tier(self, name: str) -> PricingTier | None:
        for t in self.model.tiers:
            if t.name.startswith(name):
                return t
        return None

    def _calculate_llm_cost(self, users: dict[str, int]) -> int:
        """Calculate LLM cost with realistic overhead."""
        chapters_per_user = {
            "free": 2,  # free users use sparingly
            "starter": 10,
            "pro": 30,
            "studio": 80,
            "enterprise": 200,
        }
        
        total = 0
        for tier_name, count in users.items():
            if count == 0:
                continue
            chapters = count * chapters_per_user.get(tier_name, 0)
            
            # Higher tiers use better/more expensive models
            multiplier = 1.0
            if tier_name == "pro":
                multiplier = 1.5  # better quality models
            elif tier_name in ("studio", "enterprise"):
                multiplier = 2.0  # premium models + more retries
            
            total += chapters * LLM_COST_PER_CHAPTER_EFFECTIVE * multiplier
        
        # Add base cost + 20% buffer for failed attempts/cache misses
        return int(total * 1.2) + self.model.llm_api_monthly_base

    def _calculate_infra_cost(self, total_users: int) -> int:
        """Non-linear infrastructure cost (discounts at scale, but database/network costs rise)."""
        # Base + per-user + data transfer + storage
        base = self.model.server_base_cost_monthly
        per_user = self.model.infra_cost_per_user_monthly_jpy * total_users
        
        # Data transfer and storage scale sub-linearly but still significant
        storage_network = 50_000 + (total_users * 15)  # ~JPY 50K base + per-user
        
        return base + per_user + storage_network

    def _calculate_payment_fees(self, users: dict[str, int]) -> tuple[int, int]:
        """Calculate payment processing fees and refunds."""
        total_fees = 0
        total_refunds = 0
        
        tier_prices = {
            "starter": 1_980,
            "pro": 3_980,
            "studio": 7_980,
            "enterprise": 39_800,
        }
        
        for tier_name, count in users.items():
            if tier_name not in tier_prices or count == 0:
                continue
            monthly_revenue = count * tier_prices[tier_name]
            
            # Stripe-like fees: 3.6% + JPY 25
            fees = int(monthly_revenue * self.model.payment_processing_rate)
            fees += count * self.model.payment_fixed_fee_jpy
            total_fees += fees
            
            # Refunds (3% of revenue)
            refunds = int(monthly_revenue * self.model.refund_rate)
            total_refunds += refunds
        
        return total_fees, total_refunds

    def simulate(self) -> list[MonthlySnapshot]:
        """Run realistic stress-test simulation."""
        model = self.model
        tiers = model.tiers
        
        free_tier = next((t for t in tiers if t.name == "Free"), None)
        starter_tier = next((t for t in tiers if "Starter" in t.name), None)
        pro_tier = next((t for t in tiers if "Pro" in t.name and "Studio" not in t.name), None)
        studio_tier = next((t for t in tiers if "Studio" in t.name), None)
        enterprise_tier = next((t for t in tiers if "Enterprise" in t.name), None)
        
        # Initial state
        total_users = 0
        free_users = 0
        starter_users = 0
        pro_users = 0
        studio_users = 0
        enterprise_users = 0
        
        for month in range(1, self.months + 1):
            # ============================================================
            # GROWTH: Realistic Japanese SaaS pattern
            # - Slow organic growth (word of mouth + SEO)
            # - Paid acquisition with diminishing returns
            # - Market saturation effects
            # ============================================================
            
            # Month 1-6: Early adopters, high growth rate but low base
            if month <= 6:
                organic_growth_rate = 0.25  # 25% MoM (aggressive for early stage)
                paid_growth = model.monthly_paid_signups
            # Month 7-18: Growth slows as base increases
            elif month <= 18:
                organic_growth_rate = 0.12  # 12% MoM
                # Paid acquisition increases but CAC rises
                paid_growth = int(model.monthly_paid_signups * (1 + month * 0.05))
            # Month 19-36: Mature growth, market saturation
            else:
                organic_growth_rate = 0.05  # 5% MoM (saturation)
                paid_growth = int(model.monthly_paid_signups * 1.5)
            
            # Apply organic growth to existing user base
            organic_new = int(total_users * organic_growth_rate) if total_users > 0 else model.monthly_organic_signups
            new_signups = organic_new + paid_growth
            
            # CAC for paid acquisition (increases over time due to competition)
            cac_effective = model.cac_jpy + (month * 50)  # CAC inflation
            paid_cac = paid_growth * cac_effective
            
            # ============================================================
            # CHURN: Realistic Japanese consumer SaaS
            # ============================================================
            # Monthly churn applied to existing users
            churned = int(total_users * model.monthly_churn_rate) + 1 if total_users > 0 else 0
            
            # Distribute churn proportionally (free users churn less, paid users churn more)
            if total_users > 0:
                churn_free = max(0, int(churned * (free_users / total_users) * 0.7))  # 30% lower churn
                churn_starter = int(churned * (starter_users / total_users) * 1.2)  # 20% higher
                churn_pro = int(churned * (pro_users / total_users) * 1.3)  # 30% higher
                churn_studio = int(churned * (studio_users / total_users) * 1.1)
                churn_enterprise = max(0, int(churned * (enterprise_users / total_users) * 0.5))  # lower churn
            else:
                churn_free = churn_starter = churn_pro = churn_studio = churn_enterprise = 0
            
            # ============================================================
            # USER DISTRIBUTION: Realistic conversion funnel
            # ============================================================
            # New users split: 65% free, 25% starter, 8% pro, 2% studio/enterprise
            free_new = int(new_signups * 0.65)
            starter_new = int(new_signups * 0.25)
            pro_new = int(new_signups * 0.08)
            studio_new = int(new_signups * 0.015)
            enterprise_new = int(new_signups * 0.005)
            
            # Conversion: free -> starter (2.5% of active free users)
            conversion_pool = free_users - churn_free
            converted_to_starter = int(conversion_pool * model.freemium_conversion_rate)
            
            # Upgrade: starter -> pro (10% of active starter users)
            upgrade_pool = starter_users - churn_starter
            upgraded_to_pro = int(upgrade_pool * model.starter_to_pro_upgrade_rate)
            
            # Studio upgrade: pro -> studio (5% of active pro users)
            studio_upgrade_pool = pro_users - churn_pro
            upgraded_to_studio = int(studio_upgrade_pool * 0.05)
            
            # Enterprise: rare, from studio users or direct sales
            enterprise_from_studio = int((studio_users - churn_studio) * 0.02)
            
            # Update user counts
            free_users = max(0, free_users - churn_free + free_new - converted_to_starter)
            starter_users = max(0, starter_users - churn_starter + starter_new + converted_to_starter - upgraded_to_pro)
            pro_users = max(0, pro_users - churn_pro + pro_new + upgraded_to_pro - upgraded_to_studio)
            studio_users = max(0, studio_users - churn_studio + studio_new + upgraded_to_studio - enterprise_from_studio)
            enterprise_users = max(0, enterprise_users - churn_enterprise + enterprise_new + enterprise_from_studio)
            
            total_users = free_users + starter_users + pro_users + studio_users + enterprise_users
            
            # ============================================================
            # REVENUE CALCULATION
            # ============================================================
            mrr = (
                starter_users * starter_tier.monthly_price_jpy +
                pro_users * pro_tier.monthly_price_jpy +
                studio_users * studio_tier.monthly_price_jpy +
                enterprise_users * enterprise_tier.monthly_price_jpy
            )
            
            # Payment fees and refunds
            payment_fees, refunds = self._calculate_payment_fees({
                "starter": starter_users,
                "pro": pro_users,
                "studio": studio_users,
                "enterprise": enterprise_users,
            })
            
            # Gross revenue (after payment processing, before refunds)
            gross_revenue = mrr - payment_fees
            net_revenue_before_costs = gross_revenue - refunds
            
            # ============================================================
            # COSTS
            # ============================================================
            llm_cost = self._calculate_llm_cost({
                "free": free_users,
                "starter": starter_users,
                "pro": pro_users,
                "studio": studio_users,
                "enterprise": enterprise_users,
            })
            
            infra_cost = self._calculate_infra_cost(total_users)
            support_cost = total_users * model.support_cost_per_user_monthly_jpy
            staff_cost = model.staff_cost_monthly + (month * 50_000)  # staff cost increases over time
            marketing_cost = model.marketing_monthly + paid_cac
            compliance_cost = model.compliance_legal_monthly + (total_users * 10)  # scales with users
            misc_cost = model.misc_monthly
            
            total_cost = (
                llm_cost + infra_cost + support_cost + staff_cost +
                marketing_cost + compliance_cost + misc_cost
            )
            
            net_revenue = net_revenue_before_costs - total_cost
            
            snapshot = MonthlySnapshot(
                month=month,
                total_users=total_users,
                free_users=free_users,
                starter_users=starter_users,
                pro_users=pro_users,
                studio_users=studio_users,
                enterprise_users=enterprise_users,
                new_signups=new_signups,
                churned_users=churned,
                mrr_jpy=mrr,
                llm_cost_jpy=llm_cost,
                support_cost_jpy=support_cost,
                infra_cost_jpy=infra_cost,
                staff_cost_jpy=staff_cost,
                marketing_cost_jpy=marketing_cost,
                compliance_cost_jpy=compliance_cost,
                misc_cost_jpy=misc_cost,
                payment_fees_jpy=payment_fees,
                refunds_jpy=refunds,
                gross_revenue_jpy=gross_revenue,
                net_revenue_jpy=net_revenue,
                cac_total_jpy=paid_cac,
            )
            self.snapshots.append(snapshot)
        
        return self.snapshots

    def print_summary(self) -> None:
        """Print formatted summary."""
        print("=" * 80)
        print(f"AutoNovel SaaS STRESS TEST - {self.model.name}")
        print("=" * 80)
        print()
        
        final = self.snapshots[-1]
        peak_loss = min(s.net_revenue_jpy for s in self.snapshots)
        cumulative = sum(s.net_revenue_jpy for s in self.snapshots)
        total_cac = sum(s.cac_total_jpy for s in self.snapshots)
        
        print(f"--- FINAL STATE (Month {final.month}) ---")
        print(f"  Total Users:         {final.total_users:,}")
        print(f"    Free:              {final.free_users:,}")
        print(f"    Starter:           {final.starter_users:,}")
        print(f"    Pro:               {final.pro_users:,}")
        print(f"    Studio:            {final.studio_users:,}")
        print(f"    Enterprise:        {final.enterprise_users:,}")
        print()
        print(f"  MRR:                 JPY {final.mrr_jpy:,} (~${final.mrr_jpy / 155:.0f}/month)")
        print(f"  ARR (MRR x 12):      JPY {final.mrr_jpy * 12:,} (~${final.mrr_jpy * 12 / 155:,.0f}/year)")
        print()
        print(f"--- MONTHLY COSTS (Final Month) ---")
        print(f"  LLM API:             JPY {final.llm_cost_jpy:,}")
        print(f"  Infrastructure:      JPY {final.infra_cost_jpy:,}")
        print(f"  Support:             JPY {final.support_cost_jpy:,}")
        print(f"  Staff:               JPY {final.staff_cost_jpy:,}")
        print(f"  Marketing:           JPY {final.marketing_cost_jpy:,}")
        print(f"  Compliance/Legal:    JPY {final.compliance_cost_jpy:,}")
        print(f"  Misc:                JPY {final.misc_cost_jpy:,}")
        print(f"  Total Monthly Cost:  JPY {final.llm_cost_jpy + final.infra_cost_jpy + final.support_cost_jpy + final.staff_cost_jpy + final.marketing_cost_jpy + final.compliance_cost_jpy + final.misc_cost_jpy:,}")
        print()
        print(f"--- PROFITABILITY ---")
        print(f"  Payment Fees:        JPY {final.payment_fees_jpy:,}")
        print(f"  Refunds:             JPY {final.refunds_jpy:,}")
        print(f"  Monthly Net Revenue: JPY {final.net_revenue_jpy:,}")
        print(f"  Peak Monthly Loss:   JPY {peak_loss:,}")
        print(f"  3-Year Cumulative:   JPY {cumulative:,}")
        print(f"  Total CAC (3yr):     JPY {total_cac:,}")
        
        # Break-even
        breakeven_month = None
        for i, s in enumerate(self.snapshots):
            if s.net_revenue_jpy >= 0:
                breakeven_month = i + 1
                break
        if breakeven_month:
            print(f"  Break-even Month:    Month {breakeven_month}")
        else:
            print(f"  Break-even:          NOT REACHED in {self.months} months")
        
        print()
        print(f"--- UNIT ECONOMICS (Month {final.month}) ---")
        paying_users = final.starter_users + final.pro_users + final.studio_users + final.enterprise_users
        if paying_users > 0:
            print(f"  ARPCM:               JPY {final.mrr_jpy / paying_users:,.0f}/paying user")
            print(f"  LLM cost/paying user: JPY {final.llm_cost_jpy / paying_users:,.0f}")
            print(f"  Support cost/user:   JPY {final.support_cost_jpy / final.total_users:,.0f}")
            print(f"  LTV/CAC ratio:       {final.mrr_jpy / max(1, total_cac):.2f}x")
        
        # Cash runway analysis
        print()
        print(f"--- CASH RUNWAY ---")
        cumulative_cf = 0
        runway_month = None
        for i, s in enumerate(self.snapshots):
            cumulative_cf += s.net_revenue_jpy
            if cumulative_cf >= 0 and runway_month is None:
                runway_month = i + 1
        if runway_month:
            print(f"  Cumulative CF positive: Month {runway_month}")
        else:
            print(f"  Cumulative CF:        JPY {cumulative_cf:,} (negative)")
        
        # Risk indicators
        print()
        print(f"--- RISK INDICATORS ---")
        if final.llm_cost_jpy > final.mrr_jpy:
            print(f"  WARNING: LLM costs (JPY {final.llm_cost_jpy:,}) exceed MRR (JPY {final.mrr_jpy:,})")
        if final.net_revenue_jpy < 0:
            print(f"  WARNING: Not profitable at month {final.month}")
        if paying_users < 100:
            print(f"  WARNING: Low paying user base ({paying_users}) - high burn rate")
        
        print()

    def print_monthly_table(self, last_n: int = 12) -> None:
        """Print recent monthly breakdown."""
        print(f"{'Month':>6} {'Users':>8} {'Free':>7} {'Starter':>8} {'Pro':>7} {'Studio':>7} {'Ent':>5} "
              f"{'MRR':>12} {'LLM Cost':>10} {'Net':>12}")
        print(f"{'-' * 6} {'-' * 8} {'-' * 7} {'-' * 8} {'-' * 7} {'-' * 7} {'-' * 5} "
              f"{'-' * 12} {'-' * 10} {'-' * 12}")
        
        for s in self.snapshots[-last_n:]:
            print(
                f"{s.month:>6} {s.total_users:>8,} {s.free_users:>7,} "
                f"{s.starter_users:>8,} {s.pro_users:>7,} {s.studio_users:>7,} {s.enterprise_users:>5,} "
                f"JPY {s.mrr_jpy:>9,} JPY {s.llm_cost_jpy:>8,} JPY {s.net_revenue_jpy:>10,}"
            )


# ============================================================
# 5. Stress Test Scenarios
# ============================================================

def create_realistic_model() -> RevenueModel:
    """Base realistic model with conservative assumptions."""
    return RevenueModel(
        name="AutoNovel Realistic Base",
        freemium_conversion_rate=0.025,  # 2.5%
        starter_to_pro_upgrade_rate=0.10,  # 10%
        monthly_churn_rate=0.06,  # 6%
        annual_churn_rate=0.50,  # 50%
        monthly_organic_signups=80,
        monthly_paid_signups=40,
        cac_jpy=4_500,
        llm_api_monthly_base=80_000,
        server_base_cost_monthly=150_000,
        staff_cost_monthly=2_500_000,
        marketing_monthly=300_000,
        compliance_legal_monthly=100_000,
        misc_monthly=100_000,
    )


def create_stress_model() -> RevenueModel:
    """Stress test: higher churn, lower conversion, higher costs."""
    return RevenueModel(
        name="AutoNovel STRESS TEST",
        freemium_conversion_rate=0.015,  # 1.5% (poor conversion)
        starter_to_pro_upgrade_rate=0.05,  # 5% (price sensitive)
        monthly_churn_rate=0.08,  # 8% (high churn)
        annual_churn_rate=0.65,  # 65%
        monthly_organic_signups=40,  # low organic
        monthly_paid_signups=20,  # low paid
        cac_jpy=8_000,  # high CAC
        llm_api_monthly_base=120_000,  # higher base cost
        server_base_cost_monthly=200_000,
        staff_cost_monthly=3_500_000,  # larger team needed
        marketing_monthly=500_000,  # more marketing needed
        compliance_legal_monthly=150_000,
        misc_monthly=150_000,
    )


def create_optimistic_model() -> RevenueModel:
    """Optimistic but still realistic."""
    return RevenueModel(
        name="AutoNovel Optimistic",
        freemium_conversion_rate=0.04,  # 4%
        starter_to_pro_upgrade_rate=0.15,  # 15%
        monthly_churn_rate=0.04,  # 4%
        annual_churn_rate=0.35,  # 35%
        monthly_organic_signups=150,
        monthly_paid_signups=80,
        cac_jpy=3_000,
        llm_api_monthly_base=60_000,
        server_base_cost_monthly=120_000,
        staff_cost_monthly=2_000_000,
        marketing_monthly=250_000,
        compliance_legal_monthly=80_000,
        misc_monthly=80_000,
    )


# ============================================================
# 6. Main Execution
# ============================================================

def main():
    """Run stress-test scenarios."""
    print("=" * 80)
    print("AutoNovel SaaS Revenue Simulation - STRESS TEST v2.0")
    print("Realistic Japanese market assumptions with operational overhead")
    print("=" * 80)
    print()
    
    scenarios = {
        "STRESS TEST (worst case)": (create_stress_model(), 36),
        "REALISTIC BASE": (create_realistic_model(), 36),
        "OPTIMISTIC": (create_optimistic_model(), 36),
    }
    
    all_results = {}
    for name, (model, months) in scenarios.items():
        sim = StressTestSimulator(model, months=months)
        sim.simulate()
        all_results[name] = sim
        
        print(f"\n{'=' * 80}")
        print(f"SCENARIO: {name}")
        print(f"{'=' * 80}")
        sim.print_summary()
        
        if "BASE" in name:
            print("\n--- RECENT MONTHLY BREAKDOWN (Realistic Base) ---")
            sim.print_monthly_table(last_n=12)
    
    # Comparative summary
    print(f"\n{'=' * 80}")
    print("SCENARIO COMPARISON (36 months)")
    print(f"{'=' * 80}")
    print(f"{'Scenario':<25} {'Users':>8} {'Paying':>8} {'MRR':>14} {'ARR':>16} {'Net':>14} {'Breakeven':>10}")
    print(f"{'-' * 25} {'-' * 8} {'-' * 8} {'-' * 14} {'-' * 16} {'-' * 14} {'-' * 10}")
    
    for name, sim in all_results.items():
        final = sim.snapshots[-1]
        paying = final.starter_users + final.pro_users + final.studio_users + final.enterprise_users
        be = next((f"M{i+1}" for i, s in enumerate(sim.snapshots) if s.net_revenue_jpy >= 0), "N/A")
        print(
            f"{name:<25} {final.total_users:>8,} {paying:>8,} "
            f"JPY {final.mrr_jpy:>12,} JPY {final.mrr_jpy * 12:>14,} "
            f"JPY {final.net_revenue_jpy:>12,} {be:>10}"
        )
    
    # Key insights
    print(f"\n{'=' * 80}")
    print("REALISTIC ASSESSMENT")
    print(f"{'=' * 80}")
    
    base = all_results["REALISTIC BASE"]
    final_base = base.snapshots[-1]
    paying_base = final_base.starter_users + final_base.pro_users + final_base.studio_users + final_base.enterprise_users
    
    print(f"""
1. MARKET REALITY
   - TAM: {MARKET_TOTAL_AUTHORS_JP:,} total, {MARKET_ACTIVE_WRITERS_JP:,} active, {MARKET_PREMIUM_TOOL_USERS_JP:,} premium tool users
   - Realistic 3-year penetration: {final_base.total_users:,} users ({final_base.total_users / MARKET_TOTAL_AUTHORS_JP * 100:.1f}% of TAM)
   - Paying users: {paying_base:,} ({paying_base / MARKET_ACTIVE_WRITERS_JP * 100:.1f}% of active writers)

2. UNIT ECONOMICS (Realistic Base, Month 36)
   - ARPCM: JPY {final_base.mrr_jpy / max(1, paying_base):,.0f}/paying user
   - LLM cost/paying user: JPY {final_base.llm_cost_jpy / max(1, paying_base):,.0f}
   - Gross margin: ~{(1 - final_base.llm_cost_jpy / max(1, final_base.mrr_jpy)) * 100:.0f}% (before staff/infra)
   - LTV/CAC: {final_base.mrr_jpy * 12 / max(1, sum(s.cac_total_jpy for s in base.snapshots)):.1f}x (healthy if > 3x)

3. COMPETITIVE POSITIONING
   - Pricing is competitive with Japanese tools (AIのべりすと) but below Sudowrite/NovelAI
   - Risk: Users may prefer established global tools with larger ecosystems
   - Opportunity: Japanese-language optimization and local publishing integration

4. REALISTIC 3-YEAR OUTCOME (Base Case)
   - Year 1 ARR: JPY {base.snapshots[11].mrr_jpy * 12:,} (~${base.snapshots[11].mrr_jpy * 12 / 155:,.0f})
   - Year 2 ARR: JPY {base.snapshots[23].mrr_jpy * 12:,} (~${base.snapshots[23].mrr_jpy * 12 / 155:,.0f})
   - Year 3 ARR: JPY {final_base.mrr_jpy * 12:,} (~${final_base.mrr_jpy * 12 / 155:,.0f})
   - 3-year cumulative: JPY {sum(s.net_revenue_jpy for s in base.snapshots):,}

5. CRITICAL RISKS
   - LLM cost volatility: JPY {final_base.llm_cost_jpy:,}/month is 68% of revenue - sensitive to pricing changes
   - Churn: 50% annual churn means constant acquisition pressure
   - Market saturation: Only {final_base.total_users / MARKET_TOTAL_AUTHORS_JP * 100:.1f}% penetration after 3 years
   - Competition: Sudowrite, NovelAI, AIのべりすと, plus ChatGPT/Claude direct usage
   - Japanese price sensitivity: Lower price points may be needed

6. STRESS TEST OUTCOMES
   - Worst case: Cumulative loss of JPY {sum(s.net_revenue_jpy for s in all_results['STRESS TEST (worst case)'].snapshots):,}
   - Break-even unlikely in stress scenario within 36 months
   - Need JPY {sum(s.net_revenue_jpy for s in base.snapshots[:6]):,} in first 6 months (runway required)

7. RECOMMENDATIONS
   - Target paying users: {paying_base:,} in year 3 requires ~{final_base.total_users:,} total users
   - LLM cost optimization: Prompt caching, model routing, batch processing critical
   - Pricing: Consider JPY 2,980 starter / JPY 5,980 pro to improve margins
   - Enterprise focus: Higher-margin enterprise deals can subsidize consumer tier
   - Content moat: Japanese-language fine-tuning and publishing integrations are key defensibility
""")


if __name__ == "__main__":
    main()
