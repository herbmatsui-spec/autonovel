# フリーミアム 1人あたり月額10円モデル設計

## 前提条件
- 目標: フリーユーザー1人あたり月額コスト **JPY 10**
- 現在: JPY 127/月（2話生成時）
- 削減率: **92%**

---

## 1. フリーミアムの費用構造

### 現在のコスト内訳（1フリーユーザーあたり）
```
2話生成 × JPY 63.7/話 = JPY 127.4/月
├── 入力トークン: JPY 17.5/話
├── 出力トークン: JPY 30.0/話
├── リトライ/失敗: JPY 8.0/話
└── コンテキスト構築: JPY 8.2/話
```

### 目標コスト: JPY 10/月
```
許容コスト: JPY 10/月
├── LLM費: JPY 7/月（70%）
├── インフラ: JPY 2/月（20%）
└── その他: JPY 1/月（10%）
```

---

## 2. フリーミアムモデル設計

### 2.1 利用制限の厳格化

**現行**: 3話/月（無制限に近い）
**新設計**: **1話/月**（実質お試し版）

```
Free フリーミアム
├── 生成可能: 1話/月（3,000文字まで）
├── モデル: Gemini Flash（最安値）
├── コンテキスト: 500トークン（極小）
├── 機能制限:
│   ├── GraphRAG: 利用不可
│   ├── マルチモーダル: 利用不可
│   ├── 監査・批評: 利用不可
│   └── エクスポート: TXTのみ（ZIP/EPUB不可）
└── 広告: 必須（画面下部に常時表示）
```

**コスト計算**:
- 1話生成: 500トークン（入力） + 1,500トークン（出力） = 2,000トークン
- Gemini Flash: JPY 1.8/1K tokens
- 1話あたり: JPY 3.6
- 月1話: JPY 3.6 + オーバーヘッドJPY 2.0 = **JPY 5.6/月**

### 2.2 広告収入による補填

フリーユーザーには広告を表示し、JPY 10/月を賄う。

**広告単価**（日本のWeb小説ユーザー層）:
- バナー広告: JPY 5-10/impression（CTR 1-2%）
- 動画広告（ rewarded ）: JPY 20-50/再生
- アフィリエイト: JPY 50-200/成約

**目標**: 1ユーザーあたり月額JPY 10の広告収入

実装:
```python
class AdSupportedFreeTier:
    def __init__(self, user_id: UUID):
        self.user_id = user_id
    
    def show_generation_limit_reached(self):
        """生成上限到達時の広告表示"""
        # 動画広告を視聴で+1話
        ad_reward = self.show_rewarded_video()
        if ad_reward:
            self.add_credits(1)
    
    def show_sponsored_content(self):
        """関連書籍・ツールのアフィリエイト表示"""
        # 生成結果画面に広告を挿入
        sponsored_books = affiliate_api.get_recommendations(
            genre=self.current_genre,
            limit=3
        )
        return sponsored_books
```

**広告収入見積もり**:
- 1ユーザーあたり月間5回広告表示
- 平均CTR 1.5%、平均CPM JPY 500
- 収入: 5 × (JPY 500 / 1000) × 0.015 = JPY 0.0375（低い）
-  rewarded video: 1回/月 × JPY 30 = JPY 30

**結論**: 広告だけではJPY 10/月は困難。**広告 + アフィリエイト + データ活用**の組み合わせが必要。

---

## 3. フリーミアムのビジネスモデル

### 3.1 「広告 + データ」モデル（推奨）

フリーユーザーは「広告視聴 + 行動データ提供」と引き換えに無料で利用可能。

```
┌─────────────────────────────────────────┐
│         フリーミアム ユーザー            │
│                                         │
│  得られる価値:                           │
│  ├── 1話/月の小説生成（無料）            │
│  ├── 基本的なエディタ機能                 │
│  └── コミュニティ機能                     │
│                                         │
│  対価:                                   │
│  ├── 広告視聴（ rewarded video 1回/月）  │
│  ├── 使用データの収集同意                 │
│  └── メールマガジン購読同意               │
└─────────────────────────────────────────┘

収入構造:
├── 広告収入: JPY 3/月/ユーザー
├── データ活用: JPY 2/月/ユーザー（匿名化）
├── アフィリエイト: JPY 2/月/ユーザー
└── メルマガ広告: JPY 3/月/ユーザー
合計: JPY 10/月/ユーザー
```

### 3.2 「コミュニティ貢献」モデル

フリーユーザーは「プロンプト改善への貢献」と引き換えに無料利用。

```
Free Tier = ベータテスター
├── 新機能の優先体験
├── プロンプト改善へのフィードバック
├── コミュニティでの作品共有
└── 有料機能の限定トライアル

対価:
├── quality feedback（無料の労働力）
├── データ収集（改善のための使用データ）
└── 口コミ・拡散（organic marketing）
```

**効果**: 
- ユーザーは「貢献している」感覚を得られる
- 実際の開発コスト削減（フィードバック、テスト）
- organic growth の促進

---

## 4. 具体的なプラン設計

### 4.1 5段階プラン（1人あたり月額10円フリーミアム対応）

| プラン | 月額 | クレジット | モデル | コンテキスト | 広告 | 原価/月 |
|-------|------|----------|--------|------------|------|--------|
| **Free** | ¥0 | 500 | Gemini Flash | 500トークン | 強制 | **JPY 10** |
| **Starter** | ¥2,480 | 5,000 | Gemini Flash | 5,000トークン | なし | JPY 350 |
| **Pro** | ¥4,980 | 15,000 | GPT-4o-mini | 20,000トークン | なし | JPY 1,500 |
| **Studio** | ¥9,800 | 50,000 | Claude Sonnet | 100,000トークン | なし | JPY 4,500 |
| **Enterprise** | ¥39,800 | 200,000 | カスタム | 無制限 | なし | JPY 15,000 |

**原価率**:
- Free: 広告収入で相殺 → **実質0円**
- Starter: 350 / 2,480 = **14%**（高マージン）
- Pro: 1,500 / 4,980 = **30%**（健全）
- Studio: 4,500 / 9,800 = **46%**（やや高）
- Enterprise: 15,000 / 39,800 = **38%**（B2Bは高マージン）

### 4.2 フリーミアムの機能制限

**利用可能機能**:
- ✅ 1話/月の生成（3,000文字まで）
- ✅ 簡単モード（ジャンル・主人公設定のみ）
- ✅ 基本的なエディタ（リッチテキストなし）
- ✅ TXTエクスポートのみ
- ❌ GraphRAG（知識グラフ）
- ❌ 上級者Studio
- ❌ マルチモーダル（画像/音声）
- ❌ 監査・批評機能
- ❌ 共同編集
- ❌ ePub/PDFエクスポート
- ❌ APIアクセス

**広告表示箇所**:
1. 生成結果画面の下部（バナー、300×250）
2. エディタ画面のサイドバー（160×600）
3. ダッシュボードのヘッダー（728×90）
4. エクスポート前のページ（フルスクリーン広告）

### 4.3 アップグレード導線

フリーユーザーは常に upgrade を促される:

```typescript
// フロントエンドでの表示例
const FreeUserBanner = () => {
  return (
    <div className="upgrade-prompt">
      <p>今月の残り生成回数: <strong>0/1</strong></p>
      <p> unlimited 生成するには Pro に upgrade </p>
      <button onClick={() => navigate('/pricing')}>
        Pro を見る (JPY 4,980/月)
      </button>
      <p className="trial">
        または rewarded video を見て+1話ゲット
      </p>
    </div>
  );
};
```

---

## 5. 技術実装

### 5.1 フリーユーザー専用LLMルート

```python
class FreeTierLLMRouter:
    """フリーユーザー用の最適化されたLLM呼び出し"""
    
    def __init__(self):
        self.provider = "gemini_flash"  # 最安値
        self.max_context_tokens = 500  # 極小コンテキスト
        self.max_output_tokens = 1500  # 短い出力
    
    def generate(self, prompt: str, user_id: UUID) -> str:
        # プロンプトを極限まで圧縮
        compressed_prompt = self._compress_prompt(prompt)
        
        # キャッシュを積極的に使用
        cache_key = self._get_cache_key(compressed_prompt)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        # LLM呼び出し（最小トークン）
        response = self.provider.generate(
            prompt=compressed_prompt,
            max_tokens=self.max_output_tokens,
            temperature=0.7,  # 低品質で済む
        )
        
        # キャッシュ保存（短時間のみ）
        self._save_to_cache(cache_key, response, ttl=3600)
        
        # 広告表示イベント
        analytics.track_free_generation(user_id)
        
        return response
```

### 5.2 広告配信システム

```python
class AdService:
    """フリーユーザー向け広告配信"""
    
    AD_NETWORKS = {
        "google_adsense": {"cpm": 500, "currency": "JPY"},
        "amazon_affiliate": {"commission": 0.03, "currency": "JPY"},
        "rewarded_video": {"cpa": 30, "currency": "JPY"},
    }
    
    def serve_ads(self, user_id: UUID, placement: str) -> AdResponse:
        """ユーザーに最適な広告を配信"""
        user_profile = self.get_user_profile(user_id)
        
        # 小説ジャンルに応じた広告選定
        if user_profile.favorite_genre == "fantasy":
            ads = self.get_fantasy_related_ads()
        elif user_profile.favorite_genre == "romance":
            ads = self.get_romance_related_ads()
        else:
            ads = self.get_general_ads()
        
        # 重複排除（同一ユーザーに同じ広告を繰り返さない）
        seen_ads = self.get_seen_ads(user_id)
        ads = [ad for ad in ads if ad.id not in seen_ads]
        
        return AdResponse(
            ads=ads[:3],  # 最大3件
            impression_url=self.get_impression_url(user_id)
        )
```

### 5.3 コスト監視ダッシュボード

```python
class FreeTierCostMonitor:
    """フリーミアムコストのリアルタイム監視"""
    
    def __init__(self):
        self.cost_per_user_target = 10.0  # JPY/月
        self.alert_threshold = 12.0  # 20%オーバーでアラート
    
    def check_monthly_cost(self) -> CostReport:
        total_free_users = self.get_free_user_count()
        total_llm_cost = self.get_llm_cost_for_free_tier()
        total_infra_cost = self.get_infra_cost_for_free_tier()
        
        cost_per_user = (total_llm_cost + total_infra_cost) / total_free_users
        
        if cost_per_user > self.alert_threshold:
            self.send_alert(
                f"Free tier cost per user: JPY {cost_per_user:.2f} "
                f"(target: JPY {self.cost_per_user_target})"
            )
        
        return CostReport(
            total_users=total_free_users,
            cost_per_user=cost_per_user,
            total_cost=total_llm_cost + total_infra_cost,
            status="ALERT" if cost_per_user > self.alert_threshold else "OK"
        )
```

---

## 6. 財務への影響

### 6.1 フリーミアムのコスト比較

| 項目 | 現在 | 新設計 | 削減率 |
|-----|------|--------|--------|
| 1ユーザーあたりLLM費 | JPY 63.7/話 | JPY 3.6/話 | 94% |
| 月間生成可能話数 | 2話 | 1話 | 50% |
| 月額原価 | JPY 127 | JPY 10 | 92% |
| 広告収入 | JPY 0 | JPY 10 | - |
| **実質コスト** | **JPY 127** | **JPY 0** | **100%** |

### 6.2 全体への影響（Realistic Base: 1,817フリーユーザー）

**現在**:
- フリーLLM費: 1,817 × JPY 127 = JPY 230,559/月
- 広告収入: JPY 0
- 純損失: JPY 230,559/月

**新設計後**:
- フリーLLM費: 1,817 × JPY 5.6 = JPY 10,175/月
- 広告収入: 1,817 × JPY 10 = JPY 18,170/月
- **純利益: JPY 7,995/月**

### 6.3 3年間の累積効果

| 年度 | フリーユーザー数 | 月額コスト | 月額広告収入 | 月額純利益 |
|-----|-----------------|-----------|-------------|-----------|
| Year 1 | 5,000 | JPY 28,000 | JPY 50,000 | JPY +22,000 |
| Year 2 | 10,000 | JPY 56,000 | JPY 100,000 | JPY +44,000 |
| Year 3 | 15,000 | JPY 84,000 | JPY 150,000 | JPY +66,000 |
| **3年累計** | - | JPY 2,016,000 | JPY 3,600,000 | **JPY +1,584,000** |

---

## 7. リスクと対策

### 7.1 リスク一覧

| リスク | 発生確率 | 影響度 | 対策 |
|-------|---------|--------|------|
| 広告収入が目標に届かない | 中 | 高 | 複数広告ネットワーク統合 |
| ユーザーが制限に不満 | 高 | 中 | 明確な説明 + upgrade 導線 |
| モデル品質が低すぎて離脱 | 中 | 高 | 最低限の品質基準を維持 |
| 広告ブロッカーで収入減 | 高 | 中 | rewarded video 中心に移行 |
| プライバシー規制強化 | 低 | 高 | GDPR/APPI対応 |

### 7.2 広告収入の補完策

広告収入がJPY 10/月に届かない場合の補完:

1. **データ販売（匿名化）**
   - ユーザー行動データを統計的に処理して販売
   - 小説トレンド分析（出版社向け）
   - 月額: JPY 2/ユーザー

2. **アフィリエイト強化**
   - 生成された小説に関連書籍を推薦
   - Amazon/なろうのアフィリエイトリンク
   - 月額: JPY 3/ユーザー

3. **sponsored generation**
   - 企業がスポンサーになったプロットを生成
   - 「この小説は◯◯社に提供されています」
   - 月額: JPY 2/ユーザー

---

## 8. 成功指標（KPI）

### 8.1 コスト指標
- **フリーユーザー1人あたり月額コスト**: JPY 10以下（目標）
- **LLM費/フリーユーザー**: JPY 7以下
- **インフラ費/フリーユーザー**: JPY 2以下

### 8.2 収入指標
- **広告収入/フリーユーザー**: JPY 10以上
- **アップグレード率（フリー→有料）**: 3%以上/月
- **広告CTR**: 1.5%以上

### 8.3 ユーザー体験指標
- **フリーユーザーの継続率**: 40%以上（3ヶ月後）
- **アップグレードまでの期間**: 平均14日以内
- **NPS**: 30以上

---

## 9. 実装ロードマップ

### Phase 1（Month 1-2）: 基盤構築
- [ ] フリーユーザー用LLMルーター実装
- [ ] 広告配信システム統合
- [ ] クレジット制モデル作成
- [ ] コスト監視ダッシュボード

### Phase 2（Month 3-4）: テスト
- [ ] 少数ユーザーでのA/Bテスト
- [ ] コスト測定と調整
- [ ] 広告収入の検証
- [ ] ユーザーアンケート

### Phase 3（Month 5-6）: 段階的適用
- [ ] 新規ユーザー向けに適用
- [ ] 既存ユーザーへの移行案内
- [ ] パフォーマンス最適化
- [ ] ドキュメント整備

---

## 結論

**1人あたり月額10円のフリーミアムは技術的に可能**。

**成功の鍵**:
1. モデル選択: 最も安価なGemini Flashを使用
2. コンテキスト削減: 500トークンまで圧縮
3. 広告収入: rewarded video + アフィリエイトでJPY 10/月を達成
4. データ活用: 匿名化した行動データで補填

**注意点**:
- フリーユーザーのLTVは低い（広告収入のみ）
- アップグレード率3%が生存条件
- 広告収入はネットワーク効果に依存

**推奨**: まず少数ユーザーで実証実験を行い、広告収入がJPY 10/月に届くか検証する。
