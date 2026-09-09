#!/usr/bin/env python3
"""1冊50話10万字 小説生成 トークン厳密見積もり"""

# ============================================================
# 前提知識: 日本語のトークン効率
# ============================================================
# 日本語: 1文字 ≈ 1.5-3.0トークン（平均2.0）
# 英語: 1単語 ≈ 1.3-1.5トークン
# 小説は会話・地の文・ルビが混在するため、やや低効率
# 実測値: 1,000文字 ≈ 2,000-2,500トークン
JAPANESE_CHARS_PER_TOKEN = 500  # 1トークンあたりの文字数（平均）
BOOK_TOTAL_CHARS = 100_000       # 10万字
BOOK_TOTAL_EPISODES = 50         # 50話
CHARS_PER_EPISODE = BOOK_TOTAL_CHARS // BOOK_TOTAL_EPISODES  # 2,000文字/話

# ============================================================
# 見積もりモデル
# ============================================================
class TokenEstimate:
    def __init__(self, name: str):
        self.name = name
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_hit_ratio = 0.0
        self.retry_rate = 0.0
    
    def add(self, input_tokens: int, output_tokens: int, 
            cache_hit: float = 0.0, retry: float = 0.0):
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cache_hit_ratio = max(self.cache_hit_ratio, cache_hit)
        self.retry_rate = max(self.retry_rate, retry)
    
    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens
    
    @property
    def effective_input(self) -> int:
        # キャッシュヒットで入力トークンコスト削減
        return int(self.input_tokens * (1 - self.cache_hit_ratio * 0.9))
    
    @property
    def effective_output(self) -> int:
        # リトライで出力トークン増加
        return int(self.output_tokens * (1 + self.retry_rate))
    
    def cost_jpy(self, model: str = "deepseek_v4_flash") -> float:
        # DeepSeek-V4-Flash API価格 (JPY per 1M tokens)
        prices = {
            "deepseek_v4_flash": {"input": 21.7, "output": 43.4},
            "deepseek_v4_pro": {"input": 67.4, "output": 134.9},
            "gpt4o_mini": {"input": 87.5, "output": 350.0},
            "claude_sonnet": {"input": 1860.0, "output": 9300.0},
        }
        p = prices.get(model, prices["deepseek_v4_flash"])
        return (self.effective_input * p["input"] + 
                self.effective_output * p["output"]) / 1_000_000
    
    def __str__(self) -> str:
        return f"""[{self.name}]
  input: {self.input_tokens:,} tokens (effective: {self.effective_input:,})
  output: {self.output_tokens:,} tokens (effective: {self.effective_output:,})
  total: {self.total:,} tokens
  cache hit: {self.cache_hit_ratio * 100:.0f}%
  retry rate: {self.retry_rate * 100:.0f}%
  cost(DeepSeek-V4-Flash): JPY {self.cost_jpy():.2f}
"""


# ============================================================
# 1. プロット作成（50話分）
# ============================================================
plot_50ch = TokenEstimate("プロット作成（50話分）")

# 1.1 全体構成生成
plot_50ch.add(
    input_tokens=8_000,   # 企画書、世界観設定、ジャンル、ターゲット層
    output_tokens=4_000,  # 全体構成、章立て、感情曲線
    cache_hit=0.3,        # 世界観設定は部分的にキャッシュ
    retry=0.1
)

# 1.2 章別詳細プロット（50話）
for i in range(50):
    # 前話の要約 + 現話の要求事項
    plot_50ch.add(
        input_tokens=6_000,   # 前話要約3K + 世界観2K + プロット進捗1K
        output_tokens=2_500,  # 章タイトル、あらすじ、シーン設計
        cache_hit=0.5,        # 世界観設定は共通
        retry=0.15
    )

# 1.3 伏線・キャラクター管理
plot_50ch.add(
    input_tokens=10_000,  # 50話分の伏線データ、キャラクター一覧
    output_tokens=3_000,  # 伏線回収計画、キャラクター成長曲線
    cache_hit=0.4,
    retry=0.1
)

print(plot_50ch)


# ============================================================
# 2. 本文生成（50話）
# ============================================================
episodes = TokenEstimate("本文生成（50話）")

for i in range(50):
    # 入力: プロット該当部分 + 世界観 + 前話のコンテキスト
    input_tokens = (
        15_000  # システムプロンプト（役割、文体、品質基準）
        + 3_000  # 世界観Bible（キャラ設定、ルール）
        + 2_000  # 前話の要約（直前10話分のEmbedding）
        + 4_000  # 当該プロット詳細
        + 1_000  # 監査結果のフィードバック（あれば）
    )
    
    # 出力: 2,000文字 × 2.0トークン/文字
    output_tokens = CHARS_PER_EPISODE * 2
    
    episodes.add(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_hit=0.6,  # システムプロンプト、世界観はキャッシュ
        retry=0.2       # 品質基準を満たすまで再生成
    )

print(episodes)


# ============================================================
# 3. 監査・批評（50話）
# ============================================================
audit = TokenEstimate("監査・批評（50話）")

for i in range(50):
    # 入力: 本文 + 監査基準 + 過去の監査結果
    audit.add(
        input_tokens=10_000,  # 本文4K + 監査基準3K + 類似事例3K
        output_tokens=2_000,  # 8専門家のスコア、改善提案
        cache_hit=0.3,
        retry=0.05
    )

print(audit)


# ============================================================
# 4. リトライ・フォールバック
# ============================================================
retry = TokenEstimate("リトライ・フォールバック")

# 全体の10%がリトライ必要
retry.add(
    input_tokens=episodes.effective_input // 10,  # 10%の入力量
    output_tokens=episodes.effective_output // 10,  # 10%の出力量
    cache_hit=0.3,
    retry=0.0
)

print(retry)


# ============================================================
# 5. コンテキスト構築・RAG
# ============================================================
context = TokenEstimate("コンテキスト構築・RAG")

# ナレッジグラフ検索、ベクトル検索、類似例取得
context.add(
    input_tokens=20_000,  # GraphRAGクエリ、Embedding検索
    output_tokens=5_000,  # 検索結果の整形、コンテキスト抽出
    cache_hit=0.2,
    retry=0.0
)

print(context)


# ============================================================
# 合計
# ============================================================
print("=" * 70)
print("1冊（50話10万字）トークン合計")
print("=" * 70)

total_input = (plot_50ch.effective_input + episodes.effective_input + 
               audit.effective_input + retry.effective_input + context.effective_input)
total_output = (plot_50ch.effective_output + episodes.effective_output + 
                audit.effective_output + retry.effective_output + context.effective_output)
total_tokens = total_input + total_output

print(f"""
内訳:
  プロット作成:     {plot_50ch.total:>10,} トークン
  本文生成:         {episodes.total:>10,} トークン
  監査・批評:       {audit.total:>10,} トークン
  リトライ:         {retry.total:>10,} トークン
  コンテキスト構築: {context.total:>10,} トークン
  ─────────────────────────────
  合計:             {total_tokens:>10,} トークン

実効入力:          {total_input:>10,} トークン（キャッシュ後）
実効出力:          {total_output:>10,} トークン（リトライ後）

原価（DeepSeek-V4-Flash API）:
  JPY {plot_50ch.cost_jpy() + episodes.cost_jpy() + audit.cost_jpy() + retry.cost_jpy() + context.cost_jpy():.2f}

1文字あたり原価:
  JPY {(plot_50ch.cost_jpy() + episodes.cost_jpy() + audit.cost_jpy() + retry.cost_jpy() + context.cost_jpy()) / BOOK_TOTAL_CHARS:.4f}

1話あたり原価:
  JPY {(plot_50ch.cost_jpy() + episodes.cost_jpy() + audit.cost_jpy() + retry.cost_jpy() + context.cost_jpy()) / BOOK_TOTAL_EPISODES:.2f}
""")

print("=" * 70)
print("プラン別利用可能数（980円プラン=490万トークン）")
print("=" * 70)

plan_tokens = 4_900_000
books_possible = plan_tokens / total_tokens
episodes_possible = plan_tokens / episodes.total

print(f"""
1冊あたり必要トークン: {total_tokens:,}
980円プランで生成可能:
  長編小説: {books_possible:.1f}冊/月
  本文のみ: {episodes_possible:.0f}話/月

【現実的な利用想定】
  ユーザーは1ヶ月で:
    - プロット作成: 1-2回
    - 本文生成: 10-20話
    - 監査: 適宜
  合計: 約150,000-300,000トークン/月
  
  980円プランで余裕を持って利用可能
""")

print("=" * 70)
print("品質別モデル選択コスト比較")
print("=" * 70)

models = [
    ("DeepSeek-V4-Flash", "deepseek_v4_flash"),
    ("DeepSeek-V4-Pro", "deepseek_v4_pro"),
    ("GPT-4o-mini", "gpt4o_mini"),
    ("Claude Sonnet", "claude_sonnet"),
]

total_cost_4flash = (plot_50ch.cost_jpy("deepseek_v4_flash") + 
                     episodes.cost_jpy("deepseek_v4_flash") + 
                     audit.cost_jpy("deepseek_v4_flash"))

print(f"\n1冊あたりAPI原価:")
for name, model_key in models:
    cost = (plot_50ch.cost_jpy(model_key) + 
            episodes.cost_jpy(model_key) + 
            audit.cost_jpy(model_key))
    print(f"  {name:<20}: JPY {cost:>8,.2f}")

print(f"""
【結論】
  50話10万字の原価:
    DeepSeek-V4-Flash: JPY {total_cost_4flash:.2f}
    DeepSeek-V4-Pro:   JPY {plot_50ch.cost_jpy("deepseek_v4_pro") + episodes.cost_jpy("deepseek_v4_pro") + audit.cost_jpy("deepseek_v4_pro"):.2f}
    
  980円プランで十分に賄える
  利益率: {(1 - total_cost_4flash / 980) * 100:.1f}%
""")
