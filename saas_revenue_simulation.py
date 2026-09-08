#!/usr/bin/env python3
"""AutoNovel SaaS Revenue Simulation Model (v1.0)

This module simulates revenue projections for AutoNovel as a SaaS product.
Based on Japanese web novel market data (2025-2026) and comparable SaaS tools.

Usage:
    python saas_revenue_simulation.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


# ============================================================
# 1. Market & Competitive Data (sourced from web research)
# ============================================================

MARKET_TOTAL_AUTHORS_JP = 500_000  # conservative estimate across なろう/カクヨム/エブリスタ
MARKET_ACTIVE_PREMIUM_AUTHORS_JP = 50_000  # authors who already pay for tools
MARKET_TOTAL_GLOBAL = 3_000_000  # global web novel authors (English + other languages)

COMPETITOR_PRICING_MONTHLY_USD = {
    "Sudowrite_Hobby": 10.0,
    "Sudowrite_Pro": 22.0,
    "Sudowrite_Max": 44.0,
    "NovelAI_Tablet": 10.0,
    "NovelAI_Scroll": 15.0,
    "NovelAI_Opus": 25.0,
    "AI_Naberisuto_Voyager": 9.0,   # ~¥1,160
    "AI_Naberisuto_Bungo": 16.0,    # ~¥1,980
    "ChatGPT_Plus": 20.0,
}

# Average LLM cost per novel chapter (JP, ~3000 chars, premium model)
LLM_COST_PER_CHAPTER_USD = 0.15  # using balanced quality/cost model
LLM_COST_PER_CHAPTER_JPY = LLM_COST_PER_CHAPTER_USD * 155  # ~¥23/chapter

# Average chapters generated per user per month by tier
CHAPTERS_PER_USER = {
    "free": 2,
    "starter": 8,
    "pro": 25,
    "enterprise": 100,
}


# ============================================================
# 2. Business Model Configuration
# ============================================================

@dataclass
class PricingTier:
    name: str
    monthly_price_jpy: int
    monthly_price_usd: float
    generation_limit: int | None  # None = unlimited
    features: list[str] = field(default_factory=list)
    target_audience: str = ""


@dataclass
class RevenueModel:
    """Complete SaaS revenue model configuration."""
    name: str
    currency: str = "JPY"
    tax_rate: float = 0.10  # Japanese consumption tax
    platform_fee_rate: float = 0.0  # App Store/Google Play fee if applicable
    stripe_fee_rate: float = 0.036 + 0.25  # 3.6% + ¥25 per transaction
    tiers: list[PricingTier] = field(default_factory=list)
    freemium_conversion_rate: float = 0.05  # 5% free → paid
    starter_to_pro_upgrade_rate: float = 0.15  # 15% upgrade
    monthly_churn_rate: float = 0.05  # 5% monthly churn
    annual_churn_rate: float = 0.30  # 30% annual churn (more realistic for SaaS)
    # User acquisition
    monthly_organic_signups: int = 500
    monthly_paid_signups: int = 100
    cac_jpy: int = 2_500  # Customer Acquisition Cost
    # Infrastructure (monthly, JPY)
    server_cost_per_1k_users: int = 30_000
    llm_api_monthly_base: int = 50_000  # baseline + variable
    staff_cost_monthly: int = 1_500_000  # 1.5M JPY for small team
    marketing_monthly: int = 200_000


# ============================================================
# 3. Standard Pricing Tiers (Japanese market optimized)
# ============================================================

STANDARD_TIERS = [
    PricingTier(
        name="Free",
        monthly_price_jpy=0,
        monthly_price_usd=0.0,
        generation_limit=3,
        features=[
            "3 generations/month",
            "Basic quality mode",
            "Watermarked export",
            "Community support",
        ],
        target_audience="Casual writers, trial users",
    ),
    PricingTier(
        name="Starter (かんたん)",
        monthly_price_jpy=2_480,
        monthly_price_usd=16.0,
        generation_limit=20,
        features=[
            "20 chapters/month",
            "No watermark",
            "Basic GraphRAG (50 entities)",
            "Standard export (ZIP)",
            "Email support",
        ],
        target_audience="Hobbyist web novel writers",
    ),
    PricingTier(
        name="Pro (上級者)",
        monthly_price_jpy=4_980,
        monthly_price_usd=32.0,
        generation_limit=None,  # unlimited
        features=[
            "Unlimited chapters",
            "Full GraphRAG (500 entities)",
            "Advanced Studio mode",
            "Multi-modal generation (images/audio)",
            "eBook export (EPUB/PDF)",
            "Collaboration (3 users)",
            "Priority queue",
            "Blind peer review",
            "PDCA auto-improvement",
        ],
        target_audience="Professional writers, light novel authors",
    ),
    PricingTier(
        name="Enterprise (出版)",
        monthly_price_jpy=19_800,
        monthly_price_usd=128.0,
        generation_limit=None,
        features=[
            "Unlimited everything",
            "Dedicated LLM instances",
            "Custom model fine-tuning",
            "White-label option",
            "API access",
            "Multi-user (20+)",
            "Advanced analytics dashboard",
            "Commercial publishing API integration (なろう/カクヨム/Kobo)",
            "SLA guarantee (99.9%)",
            "Dedicated support",
        ],
        target_audience="Publishing companies, production studios",
    ),
]


# ============================================================
# 4. Simulation Engine
# ============================================================

@dataclass
class MonthlySnapshot:
    month: int
    total_users: int
    free_users: int
    starter_users: int
    pro_users: int
    enterprise_users: int
    new_signups: int
    churned_users: int
    mrr_jpy: int
    llm_cost_jpy: int
    infrastructure_cost_jpy: int
    staff_cost_jpy: int
    marketing_cost_jpy: int
    gross_revenue_jpy: int
    net_revenue_jpy: int
    cac_total_jpy: int


class SaaSRevenueSimulator:
    """Monte Carlo / deterministic SaaS revenue simulator."""

    def __init__(self, model: RevenueModel, months: int = 36):
        self.model = model
        self.months = months
        self.model.tiers = STANDARD_TIERS
        self.snapshots: list[MonthlySnapshot] = []

    def _get_tier(self, name: str) -> PricingTier | None:
        for t in self.model.tiers:
            if t.name == name:
                return t
        return None

    def _calculate_llm_cost(self, users_by_tier: dict[str, int]) -> int:
        """Calculate monthly LLM API cost based on active users."""
        total_cost = 0
        for tier_name, count in users_by_tier.items():
            if tier_name == "free":
                chapters = count * CHAPTERS_PER_USER["free"]
            elif tier_name == "starter":
                chapters = count * CHAPTERS_PER_USER["starter"]
            elif tier_name == "pro":
                chapters = count * CHAPTERS_PER_USER["pro"]
            elif tier_name == "enterprise":
                chapters = count * CHAPTERS_PER_USER["enterprise"]
            else:
                chapters = 0
            # Apply tier-specific cost multiplier (Pro/Enterprise use better models)
            multiplier = 1.0
            if tier_name in ("pro", "enterprise"):
                multiplier = 2.5  # higher quality models
            total_cost += chapters * LLM_COST_PER_CHAPTER_JPY * multiplier * count
        return int(total_cost) + self.model.llm_api_monthly_base

    def _calculate_infrastructure_cost(self, total_users: int) -> int:
        """Calculate infrastructure cost (servers, DB, Redis, CDN, etc.)."""
        base = self.model.server_cost_per_1k_users * max(1, total_users // 1000)
        # Add fixed costs for DB/storage
        storage = 20_000  # ~¥20k/month for managed PostgreSQL + ChromaDB
        return base + storage

    def _calculate_effective_price(self, price: float) -> float:
        """Calculate net price after payment processing fees."""
        if price == 0:
            return 0.0
        fee = self.model.stripe_fee_rate * price
        return price - fee

    def simulate(self) -> list[MonthlySnapshot]:
        """Run the simulation for configured months."""
        model = self.model
        tiers = model.tiers

        free_tier = self._get_tier("Free")
        starter_tier = self._get_tier("Starter")
        pro_tier = self._get_tier("Pro")
        enterprise_tier = self._get_tier("Enterprise")

        # Initial state (Month 0)
        total_users = 0
        free_users = 0
        starter_users = 0
        pro_users = 0
        enterprise_users = 0
        total_churned = 0

        for month in range(1, self.months + 1):
            # Growth curve: exponential early, then linear saturation
            if month <= 6:
                growth_multiplier = 1.0 + (month * 0.3)  # 30% MoM growth early
            elif month <= 18:
                growth_multiplier = 1.0 + (6 * 0.3) + ((month - 6) * 0.15)  # 15% MoM
            else:
                growth_multiplier = 1.0 + (6 * 0.3) + (12 * 0.15) + ((month - 18) * 0.05)

            # Monthly signups (organic + paid marketing)
            organic = int(model.monthly_organic_signups * min(growth_multiplier, 3.0))
            paid_marketing = model.monthly_paid_signups
            new_signups = organic + paid_marketing

            # CAC for new paid users (paid marketing portion)
            paid_cac = paid_marketing * model.cac_jpy

            # Churn
            churned = int(total_users * model.annual_churn_rate / 12) + 1
            total_churned += churned

            # Distribute new users across tiers
            # Free tier gets ~70% of new signups initially
            free_new = int(new_signups * 0.70)
            starter_new = int(new_signups * 0.20)
            pro_new = int(new_signups * 0.08)
            enterprise_new = int(new_signups * 0.02)

            # Apply churn proportionally
            if total_users > 0:
                churn_free = int(churned * (free_users / max(1, total_users)))
                churn_starter = int(churned * (starter_users / max(1, total_users)))
                churn_pro = int(churned * (pro_users / max(1, total_users)))
                churn_enterprise = int(churned * (enterprise_users / max(1, total_users)))
            else:
                churn_free = churn_starter = churn_pro = churn_enterprise = 0

            # Convert free users → starter (freemium conversion)
            conversion_pool = free_users - churn_free
            converted = int(conversion_pool * model.freemium_conversion_rate)

            # Upgrade starter → pro
            upgrade_pool = starter_users - churn_starter
            upgraded = int(upgrade_pool * model.starter_to_pro_upgrade_rate)

            # Update user counts
            free_users = max(0, free_users - churn_free + free_new - converted)
            starter_users = max(0, starter_users - churn_starter + starter_new + converted - upgraded)
            pro_users = max(0, pro_users - churn_pro + pro_new + upgraded)
            enterprise_users = max(0, enterprise_users - churn_enterprise + enterprise_new)

            total_users = free_users + starter_users + pro_users + enterprise_users

            # MRR calculation
            mrr = (
                starter_users * starter_tier.monthly_price_jpy
                + pro_users * pro_tier.monthly_price_jpy
                + enterprise_users * enterprise_tier.monthly_price_jpy
            )

            # Costs
            llm_cost = self._calculate_llm_cost({
                "free": free_users,
                "starter": starter_users,
                "pro": pro_users,
                "enterprise": enterprise_users,
            })
            infra_cost = self._calculate_infrastructure_cost(total_users)
            staff_cost = model.staff_cost_monthly
            marketing_cost = model.marketing_monthly + paid_cac

            # Revenue after payment fees (subtract Stripe fees)
            payment_fees = (
                starter_users * (model.stripe_fee_rate * starter_tier.monthly_price_jpy)
                + pro_users * (model.stripe_fee_rate * pro_tier.monthly_price_jpy)
                + enterprise_users * (model.stripe_fee_rate * enterprise_tier.monthly_price_jpy)
            )

            gross_revenue = mrr - int(payment_fees)
            total_cost = llm_cost + infra_cost + staff_cost + marketing_cost + model.staff_cost_monthly
            net_revenue = gross_revenue - total_cost

            snapshot = MonthlySnapshot(
                month=month,
                total_users=total_users,
                free_users=free_users,
                starter_users=starter_users,
                pro_users=pro_users,
                enterprise_users=enterprise_users,
                new_signups=new_signups,
                churned_users=churned,
                mrr_jpy=mrr,
                llm_cost_jpy=llm_cost,
                infrastructure_cost_jpy=infra_cost,
                staff_cost_jpy=staff_cost,
                marketing_cost_jpy=marketing_cost,
                gross_revenue_jpy=gross_revenue,
                net_revenue_jpy=net_revenue,
                cac_total_jpy=paid_cac,
            )
            self.snapshots.append(snapshot)

        return self.snapshots

    def print_summary(self) -> None:
        """Print formatted summary of the simulation."""
        print("=" * 80)
        print("AutoNovel SaaS Revenue Simulation Results")
        print("=" * 80)
        print()

        final = self.snapshots[-1]
        peak_loss = min(s.net_revenue_jpy for s in self.snapshots)
        cumulative = sum(s.net_revenue_jpy for s in self.snapshots)

        print(f"Simulation Period: {self.months} months ({self.months // 12} years)")
        print(f"Model: {self.model.name}")
        print()
        print("--- FINAL STATE (Month {}) ---".format(final.month))
        print(f"  Total Users:         {final.total_users:,}")
        print(f"    Free:              {final.free_users:,}")
        print(f"    Starter:           {final.starter_users:,}")
        print(f"    Pro:               {final.pro_users:,}")
        print(f"    Enterprise:        {final.enterprise_users:,}")
        print()
        print(f"  MRR:                 ¥{final.mrr_jpy:,} (~${final.mrr_jpy / 155:.0f}/month)")
        print(f"  ARR (MRR × 12):      ¥{final.mrr_jpy * 12:,} (~${final.mrr_jpy * 12 / 155:,.0f}/year)")
        print()
        print("--- MONTHLY COSTS (Final Month) ---")
        print(f"  LLM API:             ¥{final.llm_cost_jpy:,}")
        print(f"  Infrastructure:      ¥{final.infrastructure_cost_jpy:,}")
        print(f"  Staff:               ¥{final.staff_cost_jpy:,}")
        print(f"  Marketing:           ¥{final.marketing_cost_jpy:,}")
        print(f"  Total Monthly Cost:  ¥{final.llm_cost_jpy + final.infrastructure_cost_jpy + final.staff_cost_jpy + final.marketing_cost_jpy:,}")
        print()
        print("--- PROFITABILITY ---")
        print(f"  Monthly Net Revenue: ¥{final.net_revenue_jpy:,}")
        print(f"  Peak Monthly Loss:   ¥{peak_loss:,}")
        print(f"  3-Year Cumulative:   ¥{cumulative:,}")
        print()

        # Break-even analysis
        breakeven_month = None
        for i, s in enumerate(self.snapshots):
            if s.net_revenue_jpy >= 0 and breakeven_month is None:
                breakeven_month = i + 1
        if breakeven_month:
            print(f"  Break-even Month:    Month {breakeven_month}")
        else:
            print(f"  Break-even:          Not reached in {self.months} months")

        print()
        print("--- SCENARIO COMPARISON ---")
        self._print_scenario_comparison()

    def _print_scenario_comparison(self) -> None:
        """Print a comparison table across conservative/base/aggressive scenarios."""
        scenarios = {
            "Conservative": self._run_variant(
                organic_signups=200,
                paid_signups=50,
                conversion_rate=0.03,
                churn_rate=0.08,
            ),
            "Base (Current)": self.snapshots,
            "Aggressive": self._run_variant(
                organic_signups=1500,
                paid_signups=300,
                conversion_rate=0.08,
                churn_rate=0.04,
            ),
        }

        print(f"  {'Scenario':<20} {'Users':>10} {'MRR':>15} {'ARR':>18} {'Monthly Net':>15} {'Breakeven':>10}")
        print(f"  {'-' * 20} {'-' * 10} {'-' * 15} {'-' * 18} {'-' * 15} {'-' * 10}")

        for name, snaps in scenarios.items():
            final = snaps[-1]
            arpcu = final.mrr_jpy / max(1, final.total_users)
            be = next(
                (f"M{i+1}" for i, s in enumerate(snaps) if s.net_revenue_jpy >= 0),
                "N/A",
            )
            print(
                f"  {name:<20} {final.total_users:>10,} "
                f"¥{final.mrr_jpy:>12,} "
                f"¥{final.mrr_jpy * 12:>15,} "
                f"¥{final.net_revenue_jpy:>12,} "
                f"{be:>10}"
            )

    def _run_variant(self, **kwargs) -> list[MonthlySnapshot]:
        """Run a variant of the simulation with different parameters."""
        variant_model = RevenueModel(
            name=f"Variant({kwargs})",
            monthly_organic_signups=kwargs.get("organic_signups", self.model.monthly_organic_signups),
            monthly_paid_signups=kwargs.get("paid_signups", self.model.monthly_paid_signups),
            freemium_conversion_rate=kwargs.get("conversion_rate", self.model.freemium_conversion_rate),
            annual_churn_rate=kwargs.get("churn_rate", self.model.annual_churn_rate),
            cac_jpy=kwargs.get("cac", self.model.cac_jpy),
            server_cost_per_1k_users=kwargs.get("infra_cost", self.model.server_cost_per_1k_users),
            llm_api_monthly_base=kwargs.get("llm_base", self.model.llm_api_monthly_base),
            staff_cost_monthly=kwargs.get("staff", self.model.staff_cost_monthly),
            marketing_monthly=kwargs.get("marketing", self.model.marketing_monthly),
        )
        sim = SaaSRevenueSimulator(variant_model, months=self.months)
        return sim.simulate()

    def to_json(self) -> str:
        """Export simulation results as JSON."""
        data = {
            "model": {
                "name": self.model.name,
                "currency": self.model.currency,
                "tiers": [
                    {
                        "name": t.name,
                        "price_jpy": t.monthly_price_jpy,
                        "price_usd": t.monthly_price_usd,
                        "limit": t.generation_limit,
                        "features": t.features,
                    }
                    for t in self.model.tiers
                ],
            },
            "snapshots": [
                {
                    "month": s.month,
                    "users": {
                        "total": s.total_users,
                        "free": s.free_users,
                        "starter": s.starter_users,
                        "pro": s.pro_users,
                        "enterprise": s.enterprise_users,
                    },
                    "mrr_jpy": s.mrr_jpy,
                    "revenue": {
                        "gross": s.gross_revenue_jpy,
                        "net": s.net_revenue_jpy,
                    },
                    "costs": {
                        "llm": s.llm_cost_jpy,
                        "infrastructure": s.infrastructure_cost_jpy,
                        "staff": s.staff_cost_jpy,
                        "marketing": s.marketing_cost_jpy,
                    },
                    "churned": s.churned_users,
                }
                for s in self.snapshots
            ],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)


# ============================================================
# 5. Scenario Definitions
# ============================================================

def create_base_model() -> RevenueModel:
    """Create base-case revenue model."""
    return RevenueModel(
        name="AutoNovel Base Case (JPY)",
        currency="JPY",
        freemium_conversion_rate=0.05,
        starter_to_pro_upgrade_rate=0.15,
        annual_churn_rate=0.30,
        monthly_organic_signups=500,
        monthly_paid_signups=100,
        cac_jpy=2_500,
        server_cost_per_1k_users=30_000,
        llm_api_monthly_base=50_000,
        staff_cost_monthly=1_500_000,
        marketing_monthly=200_000,
    )


def create_conservative_model() -> RevenueModel:
    """Create conservative scenario (slower growth, higher churn)."""
    return RevenueModel(
        name="AutoNovel Conservative",
        currency="JPY",
        freemium_conversion_rate=0.03,
        starter_to_pro_upgrade_rate=0.10,
        annual_churn_rate=0.45,
        monthly_organic_signups=200,
        monthly_paid_signups=50,
        cac_jpy=4_000,
        server_cost_per_1k_users=40_000,
        llm_api_monthly_base=80_000,
        staff_cost_monthly=1_200_000,
        marketing_monthly=100_000,
    )


def create_aggressive_model() -> RevenueModel:
    """Create aggressive growth scenario (viral, strong product-market fit)."""
    return RevenueModel(
        name="AutoNovel Aggressive Growth",
        currency="JPY",
        freemium_conversion_rate=0.08,
        starter_to_pro_upgrade_rate=0.25,
        annual_churn_rate=0.20,
        monthly_organic_signups=2_000,
        monthly_paid_signups=300,
        cac_jpy=1_500,
        server_cost_per_1k_users=20_000,
        llm_api_monthly_base=100_000,
        staff_cost_monthly=2_500_000,
        marketing_monthly=500_000,
    )


# ============================================================
# 6. Main Execution
# ============================================================

def print_detailed_monthly_table(simulator: SaaSRevenueSimulator) -> None:
    """Print a detailed monthly breakdown table."""
    print()
    print(f"{'Month':>6} {'Users':>8} {'Free':>7} {'Starter':>8} {'Pro':>7} {'Ent':>5} "
          f"{'MRR':>12} {'LLM Cost':>10} {'Net':>12}")
    print(f"{'-' * 6} {'-' * 8} {'-' * 7} {'-' * 8} {'-' * 7} {'-' * 5} "
          f"{'-' * 12} {'-' * 10} {'-' * 12}")

    for s in simulator.snapshots:
        print(
            f"{s.month:>6} {s.total_users:>8,} {s.free_users:>7,} "
            f"{s.starter_users:>8,} {s.pro_users:>7,} {s.enterprise_users:>5,} "
            f"¥{s.mrr_jpy:>10,} ¥{s.llm_cost_jpy:>8,} ¥{s.net_revenue_jpy:>10,}"
        )


def main():
    """Run all simulation scenarios."""
    print("=" * 80)
    print("AutoNovel SaaS Revenue Simulation")
    print("Japanese AI Novel Writing Platform — Financial Model v1.0")
    print("=" * 80)
    print()

    scenarios = {
        "Conservative (3年)": (create_conservative_model(), 36),
        "Base Case (3年)": (create_base_model(), 36),
        "Aggressive (3年)": (create_aggressive_model(), 36),
    }

    all_results = {}
    for name, (model, months) in scenarios.items():
        sim = SaaSRevenueSimulator(model, months=months)
        sim.simulate()
        all_results[name] = sim

        print(f"\n{'=' * 80}")
        print(f"SCENARIO: {name}")
        print(f"{'=' * 80}")
        sim.print_summary()

        # Print monthly table for base case only (too verbose otherwise)
        if "Base" in name:
            print("\n--- DETAILED MONTHLY BREAKDOWN (Base Case) ---")
            print_detailed_monthly_table(sim)

    # Key insights
    print(f"\n{'=' * 80}")
    print("KEY INSIGHTS")
    print(f"{'=' * 80}")

    base = all_results["Base Case (3年)"]
    final_base = base.snapshots[-1]

    print(f"""
1. MARKET SIZE & PENETRATION
   - TAM (Japan): ~{MARKET_TOTAL_AUTHORS_JP:,} web novel authors
   - SAM (premium-capable): ~{MARKET_ACTIVE_PREMIUM_AUTHORS_JP:,} authors
   - Base case penetration at 3 years: {final_base.total_users:,} users ({final_base.total_users / MARKET_TOTAL_AUTHORS_JP * 100:.1f}% of TAM)

2. UNIT ECONOMICS (Base Case, Month 36)
   - ARPCM (Avg Revenue Per Converting User): ¥{final_base.mrr_jpy / max(1, final_base.starter_users + final_base.pro_users + final_base.enterprise_users):,.0f}/month
   - LLM cost per paying user: ¥{final_base.llm_cost_jpy / max(1, final_base.starter_users + final_base.pro_users + final_base.enterprise_users):,.0f}/month
   - Gross margin: ~{(1 - final_base.llm_cost_jpy / max(1, final_base.mrr_jpy)) * 100:.0f}% (before staff/infra)

3. COMPARABLE TOOLS
   - Sudowrite Pro: $22/month (~¥3,400) — AutoNovel Pro at ¥4,980 is priced ~47% higher
   - NovelAI Opus: $25/month (~¥3,900) — AutoNovel Pro is ~28% higher
   - Justification: AutoNovel offers significantly more features (GraphRAG, multi-modal,
     collaborative editing, commercial publishing integration, quality audit pipeline)

4. REVENUE POTENTIAL SUMMARY (3-Year ARR, Base Case)
   - Year 1 ARR: ¥{base.snapshots[11].mrr_jpy * 12:,} (~${base.snapshots[11].mrr_jpy * 12 / 155:,.0f})
   - Year 2 ARR: ¥{base.snapshots[23].mrr_jpy * 12:,} (~${base.snapshots[23].mrr_jpy * 12 / 155:,.0f})
   - Year 3 ARR: ¥{final_base.mrr_jpy * 12:,} (~${final_base.mrr_jpy * 12 / 155:,.0f})

5. RISK FACTORS
   - LLM API cost volatility: ±30% possible with model pricing changes
   - Competitive pressure from major platforms (Crowdin, Notion AI integration)
   - Japanese market price sensitivity vs. feature richness
   - Content moderation / copyright liability
   - Need for Japanese-market-specific LLM fine-tuning

6. UPSIDE CATALYSTS
   - Enterprise publishing contracts (¥19,800/month × 50 studios = ¥11.9M MRR)
   - API access tier for agencies/bots (additional revenue stream)
   - Print-on-demand integration with Amazon KDP / 光文社
   - Vertical video / TikTok novel format export (growing trend)
   - AI voice acting partnerships (CoeFont, VOICEVOX)
""")


if __name__ == "__main__":
    main()
