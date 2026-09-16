# 黒字化案 詳細設計 v1

## 1. LLMコスト最適化 - 詳細実装設計

### 1.1 現状のコスト構造分析

AutoNovelのLLM費は1章生成あたりJPY 63.7（入力JPY 17.5 + 出力JPY 30.0 + overhead JPy 16.2）。
月間LLM費JPY 7.5Mの内訳：
- 本生成: 45%（JPY 3.4M）
- 監査・批評: 25%（JPY 1.9M）
- リトライ・失敗: 20%（JPY 1.5M）
- コンテキスト構築: 10%（JPY 0.75M）

### 1.2 プロンプトキャッシュの徹底実装

**対象箇所**: `src/services/llm_service.py`, `src/backend/tasks/generation_tasks.py`

現在の実装では、世界観設定（Bible）やキャラクター情報が毎回プロンプトに含まれるが、
これらはAnthropic/OpenAIのプロンプトキャッシュ機能を活用することで75-90%コスト削減可能。

実装方法：
```python
class CachedLLMService:
    def __init__(self, provider: str):
        self.provider = provider
        self.cache_ttl = 3600  # 1時間キャッシュ
    
    def build_cached_prompt(self, system_prompt: str, context: str) -> dict:
        """システムプロンプトをキャッシュキーとして使用"""
        cache_key = hashlib.sha256(system_prompt.encode()).hexdigest()
        
        if provider == "anthropic":
            return {
                "system": system_prompt,
                "system_cache": {
                    "type": "ephemeral",
                    "ttl_seconds": self.cache_ttl
                },
                "messages": [{"role": "user", "content": context}]
            }
        # OpenAI/Googleも同様に実装
```

**効果**: 世界観Bible（平均2,000トークン）をキャッシュ化することで、
1章あたりJPY 5.0の削減（全体の8%）。

### 1.3 モデルルーティングの導入

**対象箇所**: `src/backend/llm/factory.py`（新規）

タスクの重要度に応じてモデルを使い分ける：

| タスク種別 | 現在のモデル | 最適モデル | コスト削減率 |
|-----------|-------------|-----------|-------------|
| 簡単モード生成 | Claude Sonnet | Gemini Flash | 70% |
| 上級者モード生成 | Claude Sonnet | GPT-4o-mini | 60% |
| 監査・批評 | Claude Sonnet | Gemini Flash | 70% |
| プロット生成 | Claude Sonnet | GPT-4o-mini | 60% |
| 最終 polish | Claude Sonnet | Claude Sonnet（変更なし） | 0% |

実装：
```python
class ModelRouter:
    ROUTING_RULES = {
        "easy_mode.generate": "gemini_flash",  # JPY 3.5/1K tokens
        "advanced.generate": "gpt4o_mini",     # JPY 4.5/1K tokens
        "audit.critique": "gemini_flash",       # JPY 3.5/1K tokens
        "plot.design": "gpt4o_mini",            # JPY 4.5/1K tokens
        "final.polish": "claude_sonnet",        # JPY 12.0/1K tokens（品質優先）
    }
    
    def route(self, task_type: str, quality_requirement: str) -> str:
        if quality_requirement == "high":
            return "claude_sonnet"
        return self.ROUTING_RULES.get(task_type, "gpt4o_mini")
```

**効果**: 平均モデル単価をJPY 12.0 → JPY 5.5に削減（54%減）。

### 1.4 バッチ処理による割引活用

**対象箇所**: `src/backend/tasks/generation_tasks.py`

OpenAI/AnthropicはバッチAPIで50%割引を提供。
現在は1話ずつ同期生成しているが、複数話をまとめて非同期バッチで処理。

実装：
```python
class BatchGenerationService:
    def create_batch(self, chapters: list[ChapterRequest]) -> BatchJob:
        """複数章を1つのバッチジョブとして登録"""
        batch_requests = []
        for chapter in chapters:
            batch_requests.append({
                "custom_id": f"ch_{chapter.id}",
                "method": "POST",
                "url": "/v1/messages",  # Anthropic
                "body": {
                    "model": "claude-3-5-haiku-20241022",  # バッチ用安価モデル
                    "max_tokens": 4000,
                    "messages": chapter.prompt
                }
            })
        
        # バッチジョブ作成（50%割引）
        response = openai_client.create_batch(batch_requests)
        return BatchJob(id=response.id, status="pending")
```

**効果**: バッチ処理により月次JPY 800,000削減（全体の11%）。

### 1.5 コンテキスト圧縮率の向上

**対象箇所**: `src/services/compression/compressor.py`

現在の4層圧縮システムの圧縮率を70%→85%に向上。

施策：
1. **セマンティック重複除去の強化**
   - MinHash類似度閾値を0.8→0.9に引き上げ
   - より積極的な重複削除

2. **重要度ランク付けの精密化**
   - BookScore連携で重要度を自動判定
   - スコア70未満のコンテキストを自動除外

3. **動的予算制御**
   - モデルのコンテキストウィンドウに応じて動的に調整
   - トークン予算の90%を使い切るまで圧縮

**効果**: コンテキストトークン数30%削減 → 1章あたりJPY 10.0削減。

### 1.6 統合効果

| 施策 | 削減率 | 月次削減額 | 実装難易度 |
|-----|-------|-----------|----------|
| プロンプトキャッシュ | 8% | JPY 600,000 | 低 |
| モデルルーティング | 30% | JPY 2,250,000 | 中 |
| バッチ処理 | 11% | JPY 825,000 | 中 |
| コンテキスト圧縮 | 5% | JPY 375,000 | 低 |
| **合計** | **54%** | **JPY 4,050,000** | - |

**追加施策（中長期的）**:
- セルフホストLLM（llama.cpp/vLLM）によるAPI費ゼロ化
- エッジキャッシュ（Cloudflare Workers）でレイテンシ削減

---

## 2. 利用量課金制 - 詳細実装設計

### 2.1 現在の課題：固定額サブスクリプション

現行プラン:
- Free: 3話/月（無料）
- Starter: ¥2,480/月（20話）
- Pro: ¥4,980/月（無制限）
- Enterprise: ¥19,800/月（無制限）

問題点:
1. **ProユーザーのLLM費が売上を超過**
   - Pro: ¥4,980/月 but LLM費 ¥5,579/月（赤字）
   - 重いユーザーほど採算が悪化

2. **無駄な生成が発生**
   - 無制限プランなのでユーザーは気軽に再生成
   - 1ユーザーあたり月間平均25話（適正値の3倍）

3. **フリーユーザーの原価負担**
   - フリー: 2話/月 but LLM費 JPY 127/月
   - 広告収入 JPy 50/月では補填不可能

### 2.2 クレジット制の導入

**設計思想**: 1クレジット = 100トークン = JPY 0.35

#### プラン設計

| プラン | 月額 | クレジット | 1話あたり | 上限 |
|-------|------|----------|----------|------|
| Free | ¥0 | 500 | 3話 | 3話/月 |
| Starter | ¥2,480 | 5,000 | 3,000トークン | 30話/月 |
| Pro | ¥4,980 | 15,000 | 2,500トークン | 90話/月 |
| Studio | ¥9,800 | 50,000 | 2,000トークン | 300話/月 |
| Enterprise | ¥29,800 | 200,000 | 1,500トークン | 1,000話/月 |

**追加クレジットパック**:
- 10,000クレジット: ¥3,980（20%割引）
- 50,000クレジット: ¥14,800（40%割引）
- 200,000クレジット: ¥49,800（50%割引）

#### 実装箇所

1. **クレジット管理**: `src/backend/database/models/credit.py`（新規）
```python
class CreditAccount(Base):
    __tablename__ = "credit_accounts"
    
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"))
    balance = Column(Integer, default=0)  # クレジット残高
    monthly_allowance = Column(Integer)  # 月次付与
    last_reset = Column(DateTime)
    
    def consume(self, amount: int) -> bool:
        if self.balance >= amount:
            self.balance -= amount
            return True
        return False
```

2. **課金処理**: `src/backend/services/credit_service.py`（新規）
```python
class CreditService:
    def __init__(self, db: Session):
        self.db = db
    
    def deduct_credits(self, user_id: UUID, tokens: int) -> bool:
        """トークン使用時にクレジットを減算"""
        credits_needed = math.ceil(tokens / 100)  # 100トークン=1クレジット
        
        account = self.db.query(CreditAccount)\
            .filter_by(user_id=user_id)\
            .first()
        
        if account and account.consume(credits_needed):
            self.db.commit()
            
            # メトリクス記録
            metrics.credit_deducted.labels(
                user_id=str(user_id),
                tier=account.tier
            ).inc(credits_needed)
            
            return True
        
        # クレジット不足
        events.insufficient_credits.emit(user_id, credits_needed)
        return False
```

3. **LLM呼び出し時の引数**: `src/backend/llm/factory.py`
```python
class LLMService:
    def generate(self, prompt: str, user_id: UUID) -> str:
        # 事前にトークン数見積もり
        estimated_tokens = self.estimate_tokens(prompt, max_tokens=4000)
        
        # クレジット確認
        if not credit_service.deduct_credits(user_id, estimated_tokens):
            raise InsufficientCreditsError(
                f"Need {estimated_tokens} tokens but insufficient credits"
            )
        
        # LLM呼び出し
        response = self.provider.generate(prompt)
        
        # 実際のトークン数で精算
        actual_tokens = response.usage.total_tokens
        credit_service.adjust_credits(user_id, estimated_tokens, actual_tokens)
        
        return response.content
```

### 2.3 ユーザー体験の設計

#### ダッシュボード表示
```
┌─────────────────────────────────────┐
│ クレジット残高: 12,450 / 15,000     │
│ ████████████████████░░░░░░  83%     │
│                                     │
│ 今月の使用: 2,550クレジット         │
│ 推定LLM費: JPY 892                  │
│                                     │
│ [追加クレジット購入]                 │
│ [自動チャージ設定]                   │
└─────────────────────────────────────┘
```

#### 従量課金オプション
- **従量のみ**: 月額基本料金なし、クレジット購入のみ
- **サブスク+従量**: 月額¥2,480 + 超過分JPY 0.35/100トークン
- **定額無制限**: ¥19,800/月（Enterpriseのみ）

### 2.4 原価率の改善効果

#### Before（固定額）
- Pro: ¥4,980/月、LLM費 ¥5,579/月 → 原価率 112%（赤字）
- Starter: ¥2,480/月、LLM費 ¥1,591/月 → 原価率 64%（薄利）
- Free: ¥0/月、LLM費 ¥127/月 → 原価率 ∞（赤字）

#### After（クレジット制）
- Pro（平均的使用）: ¥4,980 + ¥1,000 = ¥5,980、LLM費 ¥3,500 → 原価率 58%（黒字）
- Pro（ヘビーユーザー）: ¥4,980 + ¥5,000 = ¥9,980、LLM費 ¥8,000 → 原価率 80%（黒字）
- Starter: ¥2,480 + ¥500 = ¥2,980、LLM費 ¥1,200 → 原価率 40%（黒字）
- Free: ¥0/月、LLM費 ¥127/月 → 広告収入¥200で補填可能

### 2.5 段階的移行計画

#### Phase 1（Month 1-2）: 新規ユーザー向け適用
- 新規登録者からクレジット制を適用
- 既存ユーザーはGrandfather clauseで固定額継続

#### Phase 2（Month 3-4）: 移行キャンペーン
- 既存ユーザーに移行ボーナス（1ヶ月分クレジット付与）
- 移行完了で次月10%割引

#### Phase 3（Month 5-6）: 完全移行
- 全ユーザーをクレジット制に移行
- 固定額プラン廃止

### 2.6 リスクと対策

| リスク | 対策 |
|-------|-----|
| ユーザーの反発 | 移行ボーナス + 明確な料金表示 |
| LLM単価変動 | クレジット単価を四半期ごとに調整 |
| 競合の価格攻勢 | 品質差別化（GraphRAG、出版連携） |
| チャーンの増加 | 自動チャージ + 使用量アラート |

### 2.7 期待効果（数値目標）

| 指標 | Before | After（6ヶ月後） | 改善率 |
|-----|--------|----------------|--------|
| MRR | JPY 7.3M | JPY 10.5M | +44% |
| LLM費 | JPY 7.5M | JPY 4.5M | -40% |
| 月次純利益 | -JPY 7.5M | +JPY 2.5M | **黒転** |
| 原価率 | 112% | 58% | -54pt |
| LTV/CAC | 0.64x | 2.5x | +291% |

### 2.8 技術的実装の優先順位

1. **Week 1-2**: クレジットモデル作成 + 管理API
2. **Week 3-4**: 課金ミドルウェア実装
3. **Week 5-6**: フロントエンドUI（ダッシュボード、購入フロー）
4. **Week 7-8**: テスト + 負荷試験
5. **Week 9-10**: 新規ユーザー向けリリース

**工数見積もり**: エンジニア2名 × 10週間 = 20人週

---

## まとめ

### 1. LLMコスト最適化
- **投資**: エンジニア工数 6人週
- **効果**: 月次JPY 4.05M削減
- **ROI**: 即座に黒転

### 2. 利用量課金制
- **投資**: エンジニア工数 20人週
- **効果**: MRR +44%、原価率 -54pt
- **ROI**: 6ヶ月後に黒字化

**推奨実行順序**:
1. まずLLMコスト最適化を最優先で実装（即座に効果）
2. 並行して利用量課金制を設計・開発
3. 6ヶ月後にクレジット制をリリース

この2施策により、**Realistic Baseシナリオで6ヶ月後に黒字化**が可能。
