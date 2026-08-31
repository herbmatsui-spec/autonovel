"""
Kindle Unlimited / DLsite 収益シミュレーション
異世界転生・悪役令嬢・R15ファンタジー × AI生成小説
"""

from dataclasses import dataclass


@dataclass
class BookConfig:
    characters: int = 50_000
    episodes: int = 50
    chars_per_episode: int = 1_000

@dataclass
class LLMCost:
    model: str
    input_tokens: int
    output_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float

    @property
    def total_cost(self) -> float:
        return (self.input_tokens / 1000) * self.cost_per_1k_input + \
               (self.output_tokens / 1000) * self.cost_per_1k_output

@dataclass
class RevenueConfig:
    kenpc_rate_per_page_jpy: float = 0.5
    avg_kenpc_pages_per_book: int = 140
    ku_reads_per_month_optimistic: int = 50
    ku_reads_per_month_realistic: int = 15
    ku_reads_per_month_pessimistic: int = 5
    dlsite_price_jpy: int = 600
    dlsite_unit_sales_monthly_optimistic: int = 20
    dlsite_unit_sales_monthly_realistic: int = 5
    dlsite_unit_sales_monthly_pessimistic: int = 1
    dlsite_commission_rate: float = 0.4

def calc_llm_cost_per_episode(
    model: str = "gemma-4-31b-it",
    output_chars: int = 1_000,
    tokens_per_char: float = 2.5,
    cost_per_1k_output: float = 0.014,
    cost_per_1k_input: float = 0.007,
) -> LLMCost:
    output_tokens = int(output_chars * tokens_per_char)
    input_tokens = int(output_tokens * 0.3)
    return LLMCost(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_per_1k_input=cost_per_1k_input,
        cost_per_1k_output=cost_per_1k_output,
    )

def calc_book_generation_cost(
    episodes: int = 50,
    model: str = "gemma-4-31b-it",
) -> float:
    cost_per_ep = calc_llm_cost_per_episode(model=model)
    ep_cost = cost_per_ep.total_cost
    planning_cost = ep_cost * 3
    worldbuilding_cost = ep_cost * 2
    style_learning_cost = ep_cost * 1
    review_cost = ep_cost * 2
    total_per_book = ep_cost * episodes + planning_cost + worldbuilding_cost + style_learning_cost + review_cost
    return total_per_book

def calc_cover_image_cost() -> float:
    return 0.05

def calc_monthly_revenue(
    books_published: int,
    months: int,
    config: RevenueConfig,
    scenario: str = "realistic"
) -> dict:
    reads_key = {
        "optimistic": "ku_reads_per_month_optimistic",
        "realistic": "ku_reads_per_month_realistic",
        "pessimistic": "ku_reads_per_month_pessimistic",
    }[scenario]

    dlsite_key = {
        "optimistic": "dlsite_unit_sales_monthly_optimistic",
        "realistic": "dlsite_unit_sales_monthly_realistic",
        "pessimistic": "dlsite_unit_sales_monthly_pessimistic",
    }[scenario]

    total_kenpc = books_published * getattr(config, reads_key) * config.avg_kenpc_pages_per_book
    total_dlsite = books_published * getattr(config, dlsite_key) * config.dlsite_price_jpy * config.dlsite_commission_rate

    return {
        "kenpc_revenue": total_kenpc * config.kenpc_rate_per_page_jpy,
        "dlsite_revenue": total_dlsite,
        "total_revenue": total_kenpc * config.kenpc_rate_per_page_jpy + total_dlsite,
    }

def run_simulation():
    book_config = BookConfig()
    revenue_config = RevenueConfig()

    print("=" * 70)
    print("[Kindle Unlimited / DLsite AI小説出版 収益シュミレーション]")
    print("  テーマ: 異世界転生・追放・悪役令嬢・R15ファンタジー")
    print("=" * 70)

    print("\n【1. コスト分析】")
    print("-" * 50)

    gemma_cost = calc_book_generation_cost(model="gemma-4-31b-it")
    print(f"gemma-4-31b-it で1冊生成コスト: ${gemma_cost:.4f} (JPY {gemma_cost*150:.0f})")

    cheap_model_cost = calc_book_generation_cost(model="gemini-3.5-flash-lite")
    print(f"gemini-3.5-flash-lite で1冊生成コスト: ${cheap_model_cost:.4f} (JPY {cheap_model_cost*150:.0f})")

    cover_cost = calc_cover_image_cost()
    print(f"表紙画像生成コスト: ${cover_cost:.4f} (JPY {cover_cost*150:.0f})")

    total_cost_per_book = gemma_cost + cover_cost
    print(f"\n1冊あたりの総コスト: ${total_cost_per_book:.4f} (JPY {total_cost_per_book*150:.0f})")

    print("\n【2. KDP Select (Kindle Unlimited) 収益モデル】")
    print("-" * 50)
    print("KENPC報酬単価: JPY 0.4-1.0/ページ（平均0.5で試算）")
    print("1冊あたりの平均ページ数: 120-160ページ（平均140ページ）")
    print("1KENPC読み = 1冊まるごと読了相当")

    print("\n【3. DLsite 収益モデル】")
    print("-" * 50)
    print("販売価格: JPY 500-800（平均600）")
    print("DLsite手数料: 60% -> 作家手取り40%")
    print("1冊あたり 手取り: JPY 240")

    print("\n" + "=" * 70)
    print("【シナリオ別 月間収益シミュレーション】")
    print("=" * 70)

    scenarios = [
        ("楽観的（新規人気作家クラス）", "optimistic"),
        ("現実的（平均的新人作家）", "realistic"),
        ("悲観的（宣伝なし・運次第）", "pessimistic"),
    ]

    print("\n週2冊 x 4週 = 月8冊出版ペース")
    print("-" * 50)

    for name, scenario in scenarios:
        books = 8
        rev = calc_monthly_revenue(books, 1, revenue_config, scenario)
        cost = books * total_cost_per_book
        profit = rev["total_revenue"] - cost * 150

        print(f"\n{name}:")
        print(f"  KU収益: JPY {rev['kenpc_revenue']:,.0f}")
        print(f"  DLsite収益: JPY {rev['dlsite_revenue']:,.0f}")
        print(f"  総収益: JPY {rev['total_revenue']:,.0f}")
        print(f"  LLMコスト: JPY {cost*150:,.0f}")
        print(f"  手取り利益: JPY {profit:,.0f}")

    print("\n" + "=" * 70)
    print("【年間スケールアップシミュレーション】")
    print("=" * 70)

    print("\n出版速度成長シナリオ（月間、本番速度で出版続けた場合）:")
    print("-" * 50)

    cumulative_books = 0
    cumulative_revenue = 0
    cumulative_cost = 0

    for month in [1, 3, 6, 12]:
        books_this_period = min(8 + (month - 1) * 2, 20)
        if month > 1:
            period_books = books_this_period - min(8 + (month - 2) * 2, 20)
        else:
            period_books = books_this_period

        rev = calc_monthly_revenue(books_this_period, 1, revenue_config, "realistic")
        period_cost = period_books * total_cost_per_book

        cumulative_books = books_this_period * month - (books_this_period - period_books) * (month - 1) if month > 1 else books_this_period
        cumulative_revenue += rev["total_revenue"]
        cumulative_cost += period_cost * 150

        print(f"\n月{month} ( 月間出版 {books_this_period}冊, 累計約{cumulative_books}冊):")
        print(f"  月間収益: JPY {rev['total_revenue']:,.0f}")
        print(f"  累計手取り: JPY {cumulative_revenue - cumulative_cost:,.0f}")

    print("\n" + "=" * 70)
    print("【重要な考察・リスク】")
    print("=" * 70)
    print("""
主要リスク:
  1. KDP政策違反: AI生成コンテンツのupload禁令（2024年春-）
     -> 、現在は緩やかに運用されているが、突然の規制強化リスク
  2. 著作権問題: 学習データへの他家IP類似生成リスク
  3. 市場飽和: 同じ手法で大量出版正在进行中->競争激化
  4. KENPC単価下落: 2023年以降下落傾向（JPY 0.5->0.4）

現実的な結論:
  - 利益率90%以上は正しいが、絶対額が微少
  - 月 JPY 5,000-30,000程度が現実的な範囲
  - 副菜代〜轻度的主業收入レベル
  - 年間スケールとKDP政策の安定性が鍵
    """)

if __name__ == "__main__":
    run_simulation()
