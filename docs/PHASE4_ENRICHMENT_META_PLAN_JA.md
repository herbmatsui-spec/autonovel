# フェーズ4: マルチモーダルエンリッチメント統合 - メタ計画書

## 1. フェーズ4の目的
**EnrichmentAgent** を新しいスキル駆動型エージェントとして実装し、WritingAgent と AuditAgent の間に配置して、生成されたテキストを以下の4機能で強化する：
1. **コンテキストトリビア挿入** - 世界観設定から関連する雑学・トリビアを自然に組み込む
2. **引用・典拠付与** - World Bible 設定資料への脚注参照を付与し信頼性を向上
3. **感覚詳細の拡充** - 抽象的な感情描写を五感ベースの具体描写に変換（Show, Don't Tell 自動化）
4. **マルチメディアシナリオ生成** - 重要シーンからマンガ台本・ラジオドラマ脚本・アニメ絵コンテ等の派生アウトラインを自動生成

## 2. 前提条件（フェーズ1-3で完了済み）
- ✅ スキル駆動型アーキテクチャ（`SkillAgent` 基底クラス、Orchestrator、manifest.yaml）
- ✅ EventBus（非同期/同期 publish）
- ✅ GraphRAGService（ハイブリッド検索）
- ✅ WritingAgent が `drafted_text` アーティファクトを生成
- ✅ AuditAgent が `drafted_text` アーティファクトを消費
- ✅ BibleAgent が World Bible を GraphRAG で管理

## 3. アーキテクチャ変更点

### 3.1 新規コンポーネント
| コンポーネント | パス | 役割 |
|--------------|------|------|
| `EnrichmentAgent` | `src/agents/enrichment_agent.py` | コアエンリッチメントロジック（SkillAgent継承） |
| `EnrichmentSkill` (v1) | `src/agents/skills/v1/enrichment_skill.py` | v1用スキルラッパー |
| `EnrichmentSkill` (v2) | `src/agents/skills/v2/enrichment_skill.py` | v2用スキルラッパー（将来のA/Bテスト用） |
| 設定 | `config/enrichment.yaml` | 重み、閾値、機能フラグ |
| プロンプト | `prompts/enrichment/` | 4機能それぞれのプロンプトテンプレート |

### 3.2 パイプライン変更
```
現在:  WritingAgent → AuditAgent → IllustrationAgent
新規:  WritingAgent → EnrichmentAgent → AuditAgent → IllustrationAgent
```

### 3.3 マニフェスト更新
`manifest.yaml` に `EnrichmentSkill` を `WritingSkill` と `AuditSkill` の間に追加

### 3.4 アーティファクトフロー
| ステージ | 入力アーティファクト | 出力アーティファクト |
|---------|-------------------|-------------------|
| WritingAgent | prompt, context | `drafted_text`, `word_count` |
| **EnrichmentAgent** | `drafted_text`, `writing_context` | `enriched_text`, `enrichment_metadata` (trivia_inserted, citations_added, sensory_expanded, multimedia_scenarios) |
| AuditAgent | `enriched_text` (フォールバック: `drafted_text`) | audit_report |

## 4. 72ステップ分解戦略

### 分類ルール
各ステップは必ず以下を満たす：
- **原子的**: 単一ファイル変更または単一論理操作
- **テスト可能**: 明示的な検証基準を持つ
- **独立実行可能**: 軽量LLMが文脈を見失わず実行可能
- **順序明確**: 前ステップへの依存関係を明記

### カテゴリ（12カテゴリ × 6ステップ = 72ステップ）
| カテゴリ | ステップ | フォーカス |
|---------|---------|-----------|
| A: 基盤・設定 | 1-6 | 設定、プロンプト、データ構造 |
| B: EnrichmentAgent コア | 7-12 | 基底クラス、execute()、アーティファクトI/O |
| C: トリビア挿入 | 13-18 | GraphRAGクエリ、LLMフィルタリング、テキスト挿入 |
| D: 引用付与 | 19-24 | ソースマッピング、脚注生成、スタイル整合性 |
| E: 感覚拡充 | 25-30 | 感情検出、感覚書き換え、Show-Don't-Tell |
| F: マルチメディアシナリオ | 31-36 | シーン検出、テンプレートレンダリング、出力形式 |
| G: スキルラッパー | 37-42 | v1/v2スキルクラス、登録 |
| H: マニフェスト統合 | 43-48 | manifest.yaml更新、依存順序 |
| I: Orchestrator配線 | 49-54 | ノード登録、アーティファクト受け渡し |
| J: EventBus統合 | 55-60 | イベント発行、ブラインドレビュー互換性 |
| K: テスト・検証 | 61-66 | 単体テスト、統合テスト、E2Eフロー |
| L: 観測性・運用 | 67-72 | メトリクス、機能フラグ、管理API、ドキュメント |

### 各ステップのチェック基準
1. **ファイル存在** - 指定パスにファイルが作成される
2. **構文有効** - Pythonインポート、YAMLパースが通る
3. **インターフェース整合** - SkillAgent/AgentResult 契約に一致
4. **テスト通過** - 新規 + 既存リグレッション
5. **循環依存なし** - マニフェストで循環なし
6. **後方互換** - 機能フラグデフォルトOFF

## 5. リスク軽減
- **機能フラグ `ENRICHMENT_ENABLED`** デフォルト `false` で安全ロールアウト
- **フォールバック**: EnrichmentAgent 失敗時は元の `drafted_text` を AuditAgent に渡す
- **トークン予算**: `context_compression.yaml` の制限を遵守
- **A/B対応**: 最初から v1/v2 構造