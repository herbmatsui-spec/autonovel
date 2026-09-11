#!/usr/bin/env python3
"""980円プラン 利益率維持計算"""

# 基準: 500クレジット=10円の利益率を維持
BASE_PRICE = 10        # JPY
BASE_TOKENS = 50_000   # トークン
BASE_COST = 1.3        # DeepSeek-V4-Flash API原価
BASE_PROFIT_RATE = 0.87  # 利益率87%
BASE_COST_RATE = 0.13    # 原価率13%

# 980円プラン（同じ利益率）
PLAN_PRICE = 980  # JPY

# 原価率を維持
plan_cost = PLAN_PRICE * BASE_COST_RATE  # 127.4円
plan_profit = PLAN_PRICE * BASE_PROFIT_RATE  # 852.6円

# DeepSeek-V4-Flash API単価（ブレンド）
API_BLENDED_JPY_PER_1M = 1.3 * (1_000_000 / 50_000)  # JPY per 1M tokens

# 980円で買えるトークン数
plan_tokens = plan_cost / (API_BLENDED_JPY_PER_1M / 1_000_000)

print("=" * 70)
print("980円プラン 利益率維持設計")
print("=" * 70)

print(f"""
基準モデル（500クレジット=10円）:
  売上: JPY {BASE_PRICE}
  原価: JPY {BASE_COST:.2f}
  利益: JPY {BASE_PROFIT_RATE * BASE_PRICE:.2f}
  利益率: {BASE_PROFIT_RATE * 100:.0f}%
  原価率: {BASE_COST_RATE * 100:.0f}%
  トークン数: {BASE_TOKENS:,}

【980円プラン】
  売上: JPY {PLAN_PRICE}
  原価: JPY {plan_cost:.2f}（利益率{BASE_PROFIT_RATE * 100:.0f}%維持）
  利益: JPY {plan_profit:.2f}
  トークン数: {plan_tokens:,.0f}
""")

# クレジット換算
CREDIT_VALUE = PLAN_PRICE / BASE_TOKENS  # 10円/50K
credits = plan_tokens / 100  # 1クレジット=100トークン

print(f"クレジット換算:")
print(f"  1クレジットあたり: JPY {CREDIT_VALUE * 100:.4f}")
print(f"  付与クレジット: {credits:,.0f}")

print("\n" + "=" * 70)
print("利用シナリオ別")
print("=" * 70)

scenarios = [
    ("プロット15話", 36_000),
    ("プロット15話 + 本文1話", 41_000),
    ("プロット15話 + 本文5話", 61_000),
    ("プロット15話 + 本文10話", 86_000),
    ("プロット15話 + 本文15話", 111_000),
    ("プロット15話 + 本文30話", 186_000),
    ("長編100話分（プロット+本文）", 500_000),
]

for name, tokens in scenarios:
    ratio = tokens / plan_tokens
    remaining = plan_tokens - tokens
    
    print(f"\n【{name}】")
    print(f"  必要トークン: {tokens:,}")
    print(f"  プランに対する比率: {ratio * 100:.1f}%")
    if remaining > 0:
        print(f"  残りトークン: {remaining:,.0f}（約{remaining // 5000}話分）")
    else:
        print(f"  超過: {abs(remaining):,.0f}トークン（追加購入必要）")

print("\n" + "=" * 70)
print("プラン比較")
print("=" * 70)

plans = [
    ("Free", 0, 500),
    ("Starter", 980, int(plan_tokens)),
    ("Pro", 2980, int(plan_tokens * 3)),
    ("Studio", 9800, int(plan_tokens * 10)),
    ("Enterprise", 29800, int(plan_tokens * 50)),
]

print(f"\n{'プラン':<12} {'月額':>8} {'トークン':>12} {'本文(5K/話)':>12} {'原価':>10} {'利益':>10}")
print(f"{'-' * 12} {'-' * 8} {'-' * 12} {'-' * 12} {'-' * 10} {'-' * 10}")

for name, price, tokens in plans:
    cost = tokens * API_BLENDED_JPY_PER_1M / 1_000_000
    profit = price - cost
    episodes = tokens // 5000
    
    print(f"{name:<12} JPY {price:>6,} {tokens:>12,} {episodes:>10}話 "
          f"JPY {cost:>8,.2f} JPY {profit:>8,.2f}")

print("\n" + "=" * 70)
print("月額980円の価値")
print("=" * 70)

print(f"""
1話あたりのコスト（本文5,000トークン）:
  API原価: JPY {5000 * API_BLENDED_JPY_PER_1M / 1_000_000:.4f}
  プラン内: 無制限
  実質1話あたり: JPY {PLAN_PRICE / (plan_tokens // 5000):.2f}

月間の利用可能量:
  プロット15話: {plan_tokens / 36000:.1f}回
  本文(5K/話): {plan_tokens / 5000:.0f}話
  長編小説1本: {plan_tokens / 111000:.1f}本（15話+プロット）

競合比較:
  Sudowrite Pro: $22/月（約JPY 3,400）→ 1.5倍の価格
  NovelAI Opus: $25/月（約JPY 3,900）→ 2.0倍の価格
  AutoNovel 980円: 同等機能 + 出版連携 → **コスパ最高**
""")

print("=" * 70)
print("結論")
print("=" * 70)

print(f"""
【980円プランの設計】
  付与トークン: {plan_tokens:,.0f}（約{plan_tokens/1000:.0f}K）
  月額利用可能:
    - プロット15話: {plan_tokens/36000:.1f}回
    - 本文: {plan_tokens/5000:.0f}話
    - 長編1本: {plan_tokens/111000:.1f}本
  
  原価: JPY {plan_cost:.2f}
  利益: JPY {plan_profit:.2f}
  利益率: {BASE_PROFIT_RATE * 100:.0f}%

【推奨構成】
  Free: 500クレジット/月（JPY 0）
  Starter: 980円/月（{plan_tokens:,.0f}トークン）
  Pro: 2,980円/月（{plan_tokens*3:,.0f}トークン）
  Studio: 9,800円/月（{plan_tokens*10:,.0f}トークン）
  Enterprise: 29,800円/月（{plan_tokens*50:,.0f}トークン + 専用API）

【差別化ポイント】
  - DeepSeek-V4-Flash採用で低価格実現
  - 500クレジット=10円フリーミアムで集客
  - 980円で実用的な量を提供
  - 出版API連携で付加価値
""")
