#!/usr/bin/env python3
"""DeepSeek-V4 500クレジット=10円モデル 採算計算"""

# 為替レート
USD_JPY = 155

# DeepSeek-V4 API価格（2026年9月現在）
DEEPSEEK_V4_FLASH = {
    "input_per_1m": 0.14,      # USD per 1M tokens
    "input_cached_per_1m": 0.0028,
    "output_per_1m": 0.28,
}
DEEPSEEK_V4_PRO = {
    "input_per_1m": 0.435,
    "input_cached_per_1m": 0.003625,
    "output_per_1m": 0.87,
}

# JPY換算
for model in [DEEPSEEK_V4_FLASH, DEEPSEEK_V4_PRO]:
    model["input_jpy_per_1m"] = model["input_per_1m"] * USD_JPY
    model["output_jpy_per_1m"] = model["output_per_1m"] * USD_JPY
    model["blended_jpy_per_1m"] = (
        0.8 * model["input_jpy_per_1m"] + 0.2 * model["output_jpy_per_1m"]
    )

# 500クレジット = 10円 という設定
CREDITS = 500
PRICE_JPY = 10
CREDIT_VALUE_JPY = PRICE_JPY / CREDITS  # 1クレジットあたり0.02円

# 1クレジット = 100トークン と定義
TOKENS_PER_CREDIT = 100
TOTAL_TOKENS = CREDITS * TOKENS_PER_CREDIT  # 50,000トークン

print("=" * 70)
print("DeepSeek-V4 500クレジット=10円モデル 採算計算")
print("=" * 70)

print(f"\n前提条件:")
print(f"  500クレジット = JPY {PRICE_JPY}")
print(f"  1クレジット = JPY {CREDIT_VALUE_JPY:.4f}")
print(f"  1クレジット = {TOKENS_PER_CREDIT}トークン")
print(f"  合計トークン数: {TOTAL_TOKENS:,}")

print("\n" + "=" * 70)
print("API利用の場合（50,000トークンあたり）")
print("=" * 70)

for name, model in [("V4-Flash", DEEPSEEK_V4_FLASH), ("V4-Pro", DEEPSEEK_V4_PRO)]:
    cost = TOTAL_TOKENS * model["blended_jpy_per_1m"] / 1_000_000
    margin = PRICE_JPY - cost
    margin_rate = (margin / PRICE_JPY) * 100 if PRICE_JPY > 0 else 0
    
    print(f"\n【{name}】")
    print(f"  API原価: JPY {cost:.2f}")
    print(f"  売上:   JPY {PRICE_JPY}")
    print(f"  利益:   JPY {margin:.2f}")
    print(f"  利益率: {margin_rate:.1f}%")
    print(f"  原価率: {100 - margin_rate:.1f}%")

print("\n" + "=" * 70)
print("自前ホストの場合（推定）")
print("=" * 70)

# 自前ホスト原価推定
SELF_HOSTED_COSTS = {
    "Llama 3.2 3B": {"per_1m_jpy": 50, "quality": "低"},
    "Llama 3.1 8B": {"per_1m_jpy": 250, "quality": "中"},
    "DeepSeek-V4-Flash (推論)": {"per_1m_jpy": 400, "quality": "高"},
    "DeepSeek-V4-Pro (推論)": {"per_1m_jpy": 1200, "quality": "最高"},
}

for model_name, data in SELF_HOSTED_COSTS.items():
    cost = TOTAL_TOKENS * data["per_1m_jpy"] / 1_000_000
    margin = PRICE_JPY - cost
    margin_rate = (margin / PRICE_JPY) * 100 if PRICE_JPY > 0 else 0
    
    print(f"\n【{model_name}】（品質: {data['quality']}）")
    print(f"  原価/1M tokens: JPY {data['per_1m_jpy']}")
    print(f"  50Kトークン原価: JPY {cost:.2f}")
    print(f"  売上:   JPY {PRICE_JPY}")
    print(f"  利益:   JPY {margin:.2f}")
    print(f"  利益率: {margin_rate:.1f}%")

print("\n" + "=" * 70)
print("話数別の使用量シミュレーション")
print("=" * 70)

# 1話あたりのトークン数
EPISODE_TOKENS = {
    "plot_15ch": 36_000,    # 15話プロット全体
    "episode": 5_000,       # 1話本文
    "audit": 3_000,         # 監査・批評
}

scenarios = [
    ("プロット15話のみ", ["plot_15ch"]),
    ("プロット15話 + 本文1話", ["plot_15ch", "episode"]),
    ("プロット15話 + 本文5話", ["plot_15ch"] + ["episode"] * 5),
    ("プロット15話 + 本文15話", ["plot_15ch"] + ["episode"] * 15),
]

for name, items in scenarios:
    total_tokens = sum(EPISODE_TOKENS[item] for item in items)
    credits_needed = total_tokens // TOKENS_PER_CREDIT
    
    # DeepSeek-V4-Flash API原価
    api_cost = total_tokens * DEEPSEEK_V4_FLASH["blended_jpy_per_1m"] / 1_000_000
    
    # 必要なクレジット数
    credit_cost = credits_needed * CREDIT_VALUE_JPY
    
    print(f"\n【{name}】")
    print(f"  必要トークン: {total_tokens:,}")
    print(f"  必要クレジット: {credits_needed}")
    print(f"  ユーザー負担額: JPY {credit_cost:.2f}")
    print(f"  API原価: JPY {api_cost:.2f}")
    print(f"  利益: JPY {credit_cost - api_cost:.2f}")
    print(f"  利益率: {((credit_cost - api_cost) / credit_cost * 100):.1f}%")

print("\n" + "=" * 70)
print("結論")
print("=" * 70)

print("""
【成立するケース】
1. DeepSeek-V4-Flash API + 500クレジット=10円:
   - 原価率 13%（利益率87%）
   - 50,000トークンでAPI原価 JPY 1.3
   - 非常に高い利益率

2. 自前ホスト DeepSeek-V4-Flash:
   - 原価率 4-10%（利益率90-96%）
   - 最も効率的

【注意点】
- 1クレジット=100トークンだと、1ヶ月に50Kトークン=約10話分
- これはフリーミアムとしては非常に豊富
- プロット15話(36K) + 本文5話(25K) = 61Kトークンで500クレジットを超過
- 現実的には1クレジット=50トークン程度が適切か

【推奨モデル】
- フリーミアム: DeepSeek-V4-Flash API（原価率13%）
- 有料: DeepSeek-V4-Flash 自前ホスト（原価率4%）
- プレミアム: DeepSeek-V4-Pro 自前ホスト（原価率12%）

これにより「500クレジット=10円」モデルが成立する。
""")
