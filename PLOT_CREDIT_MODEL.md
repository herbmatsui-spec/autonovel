# プロット課金モデル設計

## 提案内容
- **プロット作成**: 15話分 = 150クレジット（1話あたり10クレジット）
- **話数追加**: 1話増えるごと +5クレジット（差分更新）
- **本文生成**: 1話あたり別途クレジット必要

---

## 1. プロット作成の原価分析

### 現在のプロット生成コスト

```python
# src/backend/workflows/plot_generation.py 参考
class PlotGenerationService:
    def generate_15_chapter_plot(self, concept: str) -> Plot:
        """
        15話分のプロット生成
        - LLM呼び出し: 3回（全体構成 → 章別詳細 → 伏線整理）
        - 1回あたり: 入力8K + 出力4K = 12K tokens
        - 合計: 36K tokens
        - モデル: Claude Sonnet（現在）
        - コスト: 36K × JPY 12/1K = JPY 432
        """
```

### 最適化後の原価

| 施策 | 実装 | 原価 |
|-----|------|------|
| モデル変更 | Gemini Flash | JPY 126 |
| バッチ処理 | 3回→1回にまとめる | JPY 84 |
| キャッシュ | 類似プロットを再利用 | JPY 42 |
| **合計** | - | **JPY 84** |

**結論**: 15話分プロットの原価は **JPY 84**
- ユーザー課金: 150クレジット = JPY 52.5
- **原価率: 160%（赤字）**

---

## 2. 問題点と改善案

### 問題1: 原価が売上を超過

150クレジット（JPY 52.5）ではJPY 84の原価を賄えない。

### 改善案A: クレジット単価の引き上げ

```
現在: 100クレジット = JPY 35（1クレジット = JPY 0.35）
提案: 100クレジット = JPY 70（1クレジット = JPY 0.70）
```

**新価格表**:

| 項目 | クレジット | 価格 | 原価 | 原価率 |
|-----|----------|------|------|--------|
| プロット15話 | 150 | JPY 105 | JPY 84 | 80% |
| プロット追加1話 | 5 | JPY 3.5 | JPY 5.6 | 160%（課題） |
| 本文1話 | 100 | JPY 70 | JPY 63.7 | 91% |

**課題**: 追加1話の原価（JPY 5.6）が売上（JPY 3.5）を超過。

### 改善案B: 追加話のクレジット引き上げ

```
プロット追加1話 = 10クレジット（JPY 7.0）
```

**改善後**:

| 項目 | クレジット | 価格 | 原価 | 原価率 |
|-----|----------|------|------|--------|
| プロット15話 | 150 | JPY 105 | JPY 84 | 80% |
| プロット追加1話 | 10 | JPY 7.0 | JPY 5.6 | 80% |
| 本文1話 | 100 | JPY 70 | JPY 63.7 | 91% |

**改善後原価率**:
- プロット: 80%（ acceptable ）
- 本文: 91%（ still high but manageable with volume ）
- 合計: 1話あたりJPY 72.6、原価JPY 69.3 → **原価率95%**

---

## 3. 現実的なモデル設計

### 3.1 クレジット単価の再設計

**目標原価率**: 60%以下

```
1クレジット = 100トークン = JPY 0.60
```

**新価格表**:

| 項目 | クレジット | 価格 | 原価 | 原価率 |
|-----|----------|------|------|--------|
| プロット15話 | 150 | JPY 90 | JPY 84 | 93%（ still high ） |
| プロット追加1話 | 10 | JPY 6.0 | JPY 5.6 | 93% |
| 本文1話 | 120 | JPY 72 | JPY 63.7 | 88% |

**課題**: プロットの原価率が高い。対策が必要。

### 3.2 プロット原価削減策

1. **プロットの再利用を促進**
   - ユーザーが自らプロットを編集可能
   - AIによる差分更新のみ課金
   - 原価: JPY 5.6 → JPY 2.8（50%削減）

2. **プロット品質の tier 化**
   - Basic: Gemini Flash（JPY 42）
   - Premium: Claude Sonnet（JPY 84）
   - ユーザーが選択可能

3. **バッチ割引**
   - プロット10話以上: 20%割引
   - 原価: JPY 84 → JPY 67（バッチ効率化）

### 3.3 最適化後の価格表

| 項目 | クレジット | 価格 | 原価 | 原価率 |
|-----|----------|------|------|--------|
| プロット15話（Basic） | 100 | JPY 60 | JPY 42 | **70%** |
| プロット15話（Premium） | 150 | JPY 90 | JPY 84 | **93%** |
| プロット追加1話 | 8 | JPY 4.8 | JPY 2.8 | **58%** |
| 本文1話 | 120 | JPY 72 | JPY 63.7 | **88%** |

---

## 4. ユーザー体験の設計

### 4.1 プロット優先ワークフロー

```
┌─────────────────────────────────────────┐
│  ステップ1: プロット作成（必須）          │
│  - 15話分: 150クレジット                 │
│  - または5話分: 50クレジット             │
│                                         │
│  ステップ2: 本文生成（プロットから）      │
│  - 1話あたり: 120クレジット              │
│  - プロットの内容を自動的に本文化         │
│                                         │
│  ステップ3: プロット差分更新（話数追加時） │
│  - 1話追加: 10クレジット                 │
│  - 自動でプロットを拡張                  │
└─────────────────────────────────────────┘
```

### 4.2 プロット再利用の例

**ケース1: 10話のプロット → 30話の小説**
```
初期プロット: 100クレジット（10話分）
追加プロット: 40クレジット（4話分 × 10クレジット）
本文生成: 30話 × 120クレジット = 3,600クレジット
合計: 3,740クレジット = JPY 2,244
原価: JPY 42 + JPY 56 + JPY 1,911 = JPY 2,009
原価率: 89.6%
```

**ケース2: 15話のプロット → 15話の小説**
```
プロット: 150クレジット
本文: 15話 × 120クレジット = 1,800クレジット
合計: 1,950クレジット = JPY 1,170
原価: JPY 84 + JPY 955.5 = JPY 1,039.5
原価率: 88.9%
```

---

## 5. 実装設計

### 5.1 プロット管理モデル

```python
# src/backend/database/models/plot.py（新規）
class PlotProject(Base):
    __tablename__ = "plot_projects"
    
    id = Column(UUID, primary_key=True)
    user_id = Column(UUID, ForeignKey("users.id"))
    
    # プロット基本情報
    title = Column(String(200))
    total_chapters_planned = Column(Integer)  # 15
    current_chapters = Column(Integer)  # 現在の話数
    
    # プロットデータ
    chapters = Column(JSON)  # [{chapter_num, title, summary, scenes}]
    characters = Column(JSON)
    world_settings = Column(JSON)
    
    # 課金情報
    credits_spent = Column(Integer)  # 使用クレジット
    last_generation_mode = Column(String(20))  # "basic" or "premium"
    
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class PlotChapterDiff(Base):
    """プロット差分更新履歴"""
    __tablename__ = "plot_chapter_diffs"
    
    id = Column(UUID, primary_key=True)
    plot_project_id = Column(UUID, ForeignKey("plot_projects.id"))
    
    from_chapter = Column(Integer)  # 元の話数
    to_chapter = Column(Integer)  # 更新後の話数
    added_chapters = Column(JSON)  # 追加された章データ
    credits_charged = Column(Integer)  # 請求クレジット
    
    created_at = Column(DateTime)
```

### 5.2 プロット課金サービス

```python
# src/backend/services/plot_credit_service.py
class PlotCreditService:
    CREDIT_COSTS = {
        "plot_basic_15": 100,  # 15話プロット（Basic）
        "plot_premium_15": 150,  # 15話プロット（Premium）
        "plot_add_chapter": 10,  # 1話追加
        "plot_add_chapter_bulk_10": 80,  # 10話追加（20%割引）
    }
    
    def create_plot_project(self, user_id: UUID, chapters: int, mode: str) -> PlotProject:
        """新規プロット作成"""
        if chapters == 15 and mode == "basic":
            credits = self.CREDIT_COSTS["plot_basic_15"]
        elif chapters == 15 and mode == "premium":
            credits = self.CREDIT_COSTS["plot_premium_15"]
        else:
            raise ValueError("Invalid plot creation parameters")
        
        # クレジット消費
        if not credit_service.deduct_credits(user_id, credits):
            raise InsufficientCreditsError("Not enough credits for plot creation")
        
        # プロジェクト作成
        project = PlotProject(
            user_id=user_id,
            total_chapters_planned=chapters,
            current_chapters=chapters,
            last_generation_mode=mode,
            credits_spent=credits,
        )
        db.add(project)
        db.commit()
        
        # 非同期でプロット生成
        generate_plot_task.delay(project.id, mode)
        
        return project
    
    def add_chapters_to_plot(self, project_id: UUID, additional_chapters: int) -> None:
        """プロットに話数を追加"""
        project = db.query(PlotProject).get(project_id)
        
        # 差分計算
        bulk_discount = 0.8 if additional_chapters >= 10 else 1.0
        credits = int(10 * additional_chapters * bulk_discount)
        
        # クレジット消費
        credit_service.deduct_credits(project.user_id, credits)
        
        # プロット更新
        project.current_chapters += additional_chapters
        project.credits_spent += credits
        
        # 非同期で差分生成
        extend_plot_task.delay(project_id, additional_chapters)
        
        db.commit()
```

### 5.3 フロントエンドUI

```typescript
// frontend/src/components/PlotPricing.tsx
const PlotPricingTable = () => {
  return (
    <div className="pricing-table">
      <h3>プロット作成料金</h3>
      
      <div className="plan">
        <h4>Basic（15話）</h4>
        <p className="price">100クレジット</p>
        <p className="usd">JPY 60</p>
        <ul>
          <li>✓ Gemini Flash使用</li>
          <li>✓ 基本的なプロット構成</li>
          <li>✓ 伏線・キャラクター管理</li>
        </ul>
        <button>作成する</button>
      </div>
      
      <div className="plan featured">
        <h4>Premium（15話）</h4>
        <p className="price">150クレジット</p>
        <p className="usd">JPY 90</p>
        <ul>
          <li>✓ Claude Sonnet使用</li>
          <li>✓ 高品質なプロット</li>
          <li>✓ 感情曲線・カタルシス設計</li>
          <li>✓ 出版レベル品質</li>
        </ul>
        <button>作成する</button>
      </div>
      
      <div className="addon">
        <h4>話数追加</h4>
        <p>1話あたり 10クレジット（JPY 6.0）</p>
        <p>10話以上: 20%割引</p>
      </div>
    </div>
  );
};
```

---

## 6. 財務インパクト分析

### 6.1 ユーザー1人あたりの支出例

**ケースA: 初心者（5話の短編）**
```
プロット: 50クレジット（5話分）= JPY 30
本文: 5話 × 120クレジット = 600クレジット = JPY 360
合計: JPY 390/月
原価: JPY 21 + JPY 318.5 = JPY 339.5
原価率: 87.1%
```

**ケースB: 中級者（15話の連載）**
```
プロット: 150クレジット = JPY 90
本文: 15話 × 120クレジット = 1,800クレジット = JPY 1,080
合計: JPY 1,170/月
原価: JPY 84 + JPY 955.5 = JPY 1,039.5
原価率: 88.9%
```

**ケースC: 上級者（30話の長編）**
```
プロット: 150クレジット + 追加150クレジット = JPY 90 + JPY 90 = JPY 180
本文: 30話 × 120クレジット = 3,600クレジット = JPY 2,160
合計: JPY 2,340/月
原価: JPY 84 + JPY 84 + JPY 1,911 = JPY 2,079
原価率: 88.8%
```

### 6.2 従来モデルとの比較

| 項目 | 従来（固定額） | 新モデル（プロット課金） | 差分 |
|-----|--------------|---------------------|------|
| ユーザー1人あたり月額 | JPY 4,980 | JPY 1,170 | -76% |
| MRR（3,000ユーザー） | JPY 14.9M | JPY 3.5M | -76% |
| 原価/ユーザー | JPY 5,579 | JPY 1,040 | -81% |
| 原価率 | 112% | 89% | -23pt |
| 月次純利益 | -JPY 2.1M | +JPY 640K | **黒転** |

**重要な発見**:
- ユーザー1人あたり支出は76%減るが、原価も81%減る
- 原価率が112%→89%に改善され、**黒字化**
- ユーザー数は増加する（価格弾力性）

### 6.3 ユーザー数増加の仮定

| シナリオ | 価格 | ユーザー数 | MRR | 原価率 |
|---------|------|----------|-----|--------|
| 従来Pro | JPY 4,980 | 500 | JPY 2.5M | 112% |
| 新モデル | JPY 1,170/月 | 2,000 | JPY 2.3M | 89% |

**価格を76%下げてもユーザー数4倍でMRR維持**。

---

## 7. 実装ロードマップ

### Phase 1（Month 1-2）: クレジットシステム
- [ ] クレジットモデル作成
- [ ] プロット専用クレジット管理
- [ ] 差分更新ロジック

### Phase 2（Month 3-4）: LLM統合
- [ ] プロット生成パイプライン分離
- [ ] Basic/Premiumモデル切替
- [ ] バッチ処理実装

### Phase 3（Month 5-6）: UI/UX
- [ ] プロット管理画面
- [ ] 料金表・購入フロー
- [ ] 使用量ダッシュボード

---

## 8. リスクと対策

| リスク | 影響 | 対策 |
|-------|------|------|
| プロット品質のばらつき | ユーザー不満 | Basic/Premium明確化 |
| 差分更新の失敗 | データ整合性 | ロールバック機能 |
| ユーザーの混乱 | コンバージョン低下 | 段階的な移行 |
| 原価率の上昇 | 利益圧迫 | 定期的な見直し |

---

## 9. 結論

**プロット課金モデルは有効**。

**メリット**:
1. 原価率89%で黒字化可能
2. ユーザー負担額の低減で獲得数増加
3. プロットを資産として管理することで価値向上

**デメリット**:
1. MRRは従来比76%減
2. ユーザー数4倍が必要
3. システム複雑性増加

**推奨**: 
- Phase 1でクレジット制を導入
- Phase 2でプロット課金を追加
- A/Bテストで最適な価格を検証

**最終的なモデル**:
```
1クレジット = JPY 0.60
プロット15話: 150クレジット（JPY 90）
プロット追加: 10クレジット/話（JPY 6.0）
本文: 120クレジット/話（JPY 72）
```

このモデルで**原価率89%、ユーザー1人あたり月額JPY 1,170**を実現。
