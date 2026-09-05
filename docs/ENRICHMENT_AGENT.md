# EnrichmentAgent ドキュメント

## 概要

EnrichmentAgent は、AutoNovel のマルチエージェントパイプラインにおいて、WritingAgent と AuditAgent の間に配置され、生成された原稿テキストを以下の4つの機能でエンリッチメント（付加価値化）するスキルエージェントです。

1. **トリビア挿入** - 世界観設定から関連する雑学・トリビアを自然に組み込む
2. **引用・典拠付与** - World Bible 設定資料への脚注参照を付与し信頼性を向上
3. **感覚詳細の拡充** - 抽象的な感情描写を五感ベースの具体描写に変換（Show, Don't Tell 自動化）
4. **マルチメディアシナリオ生成** - 重要シーンからマンガ台本・ラジオドラマ脚本・アニメ絵コンテ等の派生アウトラインを自動生成

## アーキテクチャ

### パイプライン位置

```
WritingAgent → EnrichmentAgent → AuditAgent → IllustrationAgent
```

### アーティファクトフロー

| ステージ | 入力 | 出力 |
|---------|------|------|
| WritingAgent | prompt, context | `drafted_text`, `word_count` |
| **EnrichmentAgent** | `drafted_text`, `writing_context` | `enriched_text`, `enrichment_metadata` |
| AuditAgent | `enriched_text` (fallback: `drafted_text`) | audit_report |

### enrichment_metadata 構造

```json
{
  "trivia": [
    {"position": 123, "original": "...", "enriched": "...", "trivia_source": "world_bible", "entity": "魔法システムA", "relevance": 0.85}
  ],
  "citations": [
    {"marker": 1, "claim": "魔法システムAはMPを10消費する", "source": {"source": "世界観設定書・巻I", "page": "p.23"}, "score": 0.9}
  ],
  "sensory": [
    {"original_phrase": "彼は悲しかった", "expanded_text": "彼の頬を伝う冷たい涙が...", "emotion": "sadness", "senses_covered": ["visual", "tactile", "auditory"]}
  ],
  "multimedia": {
    "manga_script": {...},
    "radio_drama": {...},
    "anime_storyboard": {...},
    "live_action_shots": {...}
  }
}
```

## 設定

### 設定ファイル: `config/enrichment.yaml`

```yaml
enrichment:
  enabled: false  # 機能フラグ（安全ロールアウト用）
  trivia_insertion:
    enabled: true
    max_insertions_per_chapter: 5
    relevance_threshold: 0.7
    sources: ["world_bible", "historical_facts", "cultural_trivia"]
  citation_attachment:
    enabled: true
    style: "footnote"  # footnote, bracket, endnote
    max_citations_per_chapter: 10
    source_priority: ["world_bible", "canon_material", "historical_records"]
  sensory_expansion:
    enabled: true
    target_emotions: ["sadness", "anger", "fear", "joy", "surprise", "disgust"]
    expansion_ratio: 2.5
    show_dont_tell: true
  multimedia_scenarios:
    enabled: true
    formats: ["manga_script", "radio_drama", "anime_storyboard", "live_action_shots"]
    trigger_scenes: ["climax", "battle", "emotional_peak", "revelation", "romance"]
  token_budget:
    max_enrichment_tokens: 1500
    reserve_for_audit: 500
```

### 機能フラグ

環境変数 `ENRICHMENT_ENABLED` または設定 `settings.ENRICHMENT_ENABLED` で制御（デフォルト: `false`）。

- `false` (デフォルト): EnrichmentAgent はパススルーとして動作し、元のテキストをそのまま AuditAgent に渡す
- `true`: 全エンリッチメント機能が有効

## 4つのエンリッチメント機能詳細

### 1. トリビア挿入 (Trivia Insertion)

**処理フロー:**
1. シーン文脈とエンティティを抽出
2. GraphRAG ハイブリッド検索でトリビア候補を取得（最大20件）
3. 関連度スコアリング（Jaccard類似度 + エンティティマッチボーナス + ソース重み）
4. 閾値（デフォルト 0.7）以上のトリビアを選択、最大挿入数（デフォルト 5）まで
5. 自然な挿入ポイント検出（段落区切り → 文末 → 等間隔）
5. 文脈に合わせた書き換え（視点・時制維持）
6. メタデータ記録

**出力例:**
```json
{
  "trivia": [
    {
      "position": 234,
      "enriched": "この街は紀元前時代に築かれた要塞都市で、石畳はローマ時代のものだ。",
      "trivia_source": "world_bible",
      "entity": "王都",
      "relevance": 0.82
    }
  ]
}
```

### 2. 引用・典拠付与 (Citation Attachment)

**処理フロー:**
1. World Bible 索引構築（キーワード逆引き）
2. 事実記述抽出（設定用語を含む断定文を文単位で検出）
3. キーワードベースソースマッチング（閾値 0.5）
3. 脚注マーカー `[^n]` 挿入（同一ソースは同一番号）
4. 文献リスト生成（スタイル: footnote/bracket/endnote）

**出力例:**
```markdown
主人公は魔法システムAを使って戦った[^1]。

【参考文献】
[^1] 世界観設定書・巻I p.23 - 魔法システムAはMPを10消費する
```

### 3. 感覚詳細の拡充 (Sensory Expansion)

**処理フロー:**
1. 抽象的感情フレーズ検出（6基本感情 × パターンマッチング）
2. 感情→感覚マッピング（6感情 × 5感覚 = 30カテゴリ）
3. シーン文脈ベースの感覚選択（雨→触覚/聴覚/嗅覚優先など）
4. 視点（一人称/三人称）に応じた主語調整
5. 後ろから置換で位置ズレ防止

**感情→感覚マッピング例 (sadness):**
- visual: 涙がこぼれる、視界が滲む
- auditory: 静寂が耳に痛い、遠くの音がかすかに聞こえる
- tactile: 頬を伝う冷たい涙、胸が締め付けられる
- olfactory: 雨の匂い、古い紙の匂い
- gustatory: 口の中の塩味、苦い渋み

**出力例:**
```
彼は悲しかった。 → 彼の頬を伝う冷たい涙が、石畳の凍りついた感覚を鋭く際立たせた。遠くから聞こえるサイレンの音が、彼の緊張をさらに高めていた。革の手袋のざらつきが、剣の柄をしっかりと捉えていることを伝えていた。
```

### 4. マルチメディアシナリオ生成

**トリガーシーン:** climax, battle, emotional_peak, revelation, romance

**出力フォーマット:**

| フォーマット | 構造 | 用途 |
|------------|------|------|
| manga_script | ページ → コマ（画面描写、セリフ、効果音、カメラ） | マンガ制作 |
| radio_drama | キュー（効果音、BGM、ナレーション、セリフ、演技指示） | ラジオドラマ制作 |
| anime_storyboard | カット（秒数、カメラ、アクション、セリフ、背景、作画指示、エフェクト） | アニメ制作 |
| live_action_shots | ショット（スラッグ、ショットタイプ、レンズ、移動、出演者、VFX、照明） | 実写映像制作 |

## 管理API

### エンドポイント

| エンドポイント | メソッド | 説明 |
|--------------|--------|------|
| `/admin/enrichment/status` | GET | 設定・機能フラグ・ステータス取得 |
| `/admin/enrichment/test` | POST | サンプルテキストでテスト実行 |
| `/admin/enrichment/metrics` | GET | Prometheusメトリクススナップショット |

### リクエスト例

```bash
# ステータス取得
curl http://localhost:8200/admin/enrichment/status

# テスト実行
curl -X POST http://localhost:8200/admin/enrichment/test \
  -H "Content-Type: application/json" \
  -d '{
    "draft_text": "主人公は魔法システムAを使って戦った。悲しかった。",
    "writing_context": {"location": "王都", "characters": ["主人公"]},
    "book_id": 1
  }'
```

## メトリクス (Prometheus)

| メトリクス名 | タイプ | ラベル | 説明 |
|------------|-------|--------|------|
| `enrichment_duration_seconds` | Histogram | status | 実行時間 |
| `enrichment_trivia_insertions_total` | Counter | book_id, status | トリビア挿入数 |
| `enrichment_citations_added_total` | Counter | book_id, style | 引用付与数 |
| `enrichment_sensory_expansions_total` | Counter | book_id, emotion | 感覚拡充数 |
| `enrichment_multimedia_scenarios_total` | Counter | book_id, format | マルチメディア生成数 |
| `enrichment_token_usage` | Histogram | book_id | トークン使用量差分 |
| `enrichment_errors_total` | Counter | error_type, stage | エラー数 |

## ヘルスチェック

`/health` エンドポイントに `enrichment_agent` チェックが追加されます。

チェック項目:
- 機能フラグ (`ENRICHMENT_ENABLED`)
- LLM API キー設定 (`GEMINI_API_KEY`)
- RAG サービス初期化状態
- プロンプトテンプレート読み込み状態

## トラブルシューティング

### よくある問題

| 症状 | 原因 | 対処 |
|------|------|------|
| Enrichment が実行されない | `ENRICHMENT_ENABLED=false` | 環境変数を `true` に設定 |
| トリビアが挿入されない | 関連度スコアが閾値未満 | `relevance_threshold` を下げる、または文脈を充実させる |
| 引用が付かない | Bible 索引が空 | GraphRAG/World Bible データを確認 |
| 感覚拡充されない | 感情パターン不一致 | パターン辞書を拡充、またはカスタム追加 |
| マルチメディア生成されない | トリガーシーン非該当 | シーン分類キーワードを確認・追加 |

### デバッグ方法

1. 管理API `/admin/enrichment/test` で単体テスト実行
2. ログレベルを `DEBUG` に設定して詳細ログ確認
3. Prometheus メトリクス `/metrics` で実行統計確認
4. ヘルスチェック `/health` で依存関係状態確認

## 今後の拡張予定

- [ ] LLMベースのトリビア書き換え（現在はプレースホルダー）
- [ ] 多言語対応（英語プロンプトテンプレート）
- [ ] A/B テスト用 v2 実装（感覚拡充アルゴリズム改良版）
- [ ] 動画生成プロンプト対応（Sora/Runway 形式）
- [ ] リアルタイムプレビュー機能（Studio統合）