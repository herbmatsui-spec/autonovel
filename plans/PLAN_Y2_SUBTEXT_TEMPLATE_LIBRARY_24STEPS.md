# PLAN_Y2: サブテキスト・テンプレートライブラリ実装計画（24ステップ）

## 概要
作家が編集・拡張可能な Jinja2 テンプレート群で「サブテキストの型」を資産化。文脈（感情×力関係×関係性）で決定論的にテンプレートを選択・レンダリング。

## 前提
- Jinja2 環境既存利用可
- テンプレートは `templates/subtext/` 以下で Git 管理
- 作家は YAML フロントマターでメタデータ指定

---

## ステップ一覧

### Phase 1: 基盤・テンプレート仕様策定（Step 1-6）

#### Step 1: ディレクトリ構造・命名規約策定・雛形作成
```
templates/subtext/
  ├─ _base.j2                    # 共通マクロ・フィルタ
  ├─ index.yaml                  # カタログ・検索インデックス
  ├─ betrayal/
  │   ├─ cold_acceptance.j2
  │   ├─ masked_rage.j2
  │   └─ quiet_threat.j2
  ├─ grief/
  │   ├─ denial_through_action.j2
  │   └─ suppressed_tears.j2
  └─ power_play/
      ├─ ironic_politeness.j2
      └─ silence_as_weapon.j2
```
- **テスト**: `test_template_structure.py` - 命名規約・必須メタ項目検証

#### Step 2: テンプレートメタデータスキーマ定義
- フロントマター（YAML）必須項目:
```yaml
---
id: betrayal.cold_acceptance
tags: [betrayal, cold, acceptance, irony]
context:
  emotion: [betrayal, hurt]
  power_dynamic: [inferior, equal]
  relationship: [former_ally, lover, subordinate]
  intensity: [high, medium]
variables:
  - acceptance_phrase: "受け入れの言葉"
  - dry_action: "乾いた動作"
  - hidden_emotion_action: "隠された感情の動作"
weight: 100
final: true
---
```
- **テスト**: `test_frontmatter_schema.py` - バリデーション・必須項目チェック

#### Step 3: テンプレートローダー・インデックス構築
- `TemplateLoader` クラス：ディレクトリ走査→フロントマター解析→インデックス構築
- `index.yaml` 自動生成・キャッシュ（mtime で差分更新）
- **テスト**: `test_template_loader.py` - 読み込み・インデックス再構築・キャッシュ無効化確認

#### Step 4: コンテキストマッチングエンジン実装
- `ContextMatcher.match(context: SubtextContext) -> list[TemplateCandidate]`
- タグ・コンテキスト条件でフィルタ → `weight` 降順 → `final` 優先
- 複数候補時は確率的選択（シード固定で再現性確保）
- **テスト**: `test_context_matcher.py` - 条件一致・重み・確率分布・エッジケース

#### Step 5: Jinja2 環境・カスタムフィルタ・マクロ整備
- `_base.j2` に共通フィルタ定義：`beat`, `action`, `irony`, `pause`, `glance`
- マクロ: `render_line(speaker, text)`, `render_beat(desc)`, `render_action(desc)`
- **テスト**: `test_jinja_env.py` - フィルタ・マクロ動作・エスケープ確認

#### Step 6: テンプレートレンダラ・統合インターフェース
- `TemplateRenderer.render(template_id, variables, context) -> RenderedDialogue`
- 出力構造: `{lines: [{speaker, text, type: "dialogue|beat|action"}], meta: {...}}`
- 変数不足時のデフォルト値・バリデーション
- **テスト**: `test_renderer.py` - 正常系・変数不足・型不正・XSS対策確認

---

### Phase 2: コアテンプレート資産制作（Step 7-14）

#### Step 7: 基盤テンプレート 5 種実装（betrayal カテゴリ）
- `cold_acceptance.j2`, `masked_rage.j2`, `quiet_threat.j2`, `false_forgiveness.j2`, `calculated_retreat.j2`
- 各テンプレート：台詞1行＋ト書き1-2行、変数 3-4 個
- **テスト**: `test_templates_betrayal.py` - 全テンプレートレンダリング・出力形式確認

#### Step 8: grief カテゴリ 4 種実装
- `denial_through_action.j2`, `suppressed_tears.j2`, `quiet_breakdown.j2`, `stoic_endurance.j2`
- 悲嘆の段階（否認・抑圧・静かな崩壊・耐忍）を網羅
- **テスト**: `test_templates_grief.py` - 感情段階別出力確認

#### Step 9: power_play カテゴリ 4 種実装
- `ironic_politeness.j2`, `silence_as_weapon.j2`, `feigned_ignorance.j2`, `conditional_compliance.j2`
- 権力関係（上位/下位/対等）× 意図（威圧/試探/譲歩）マトリクス
- **テスト**: `test_templates_power_play.py` - 権力文脈別適切選択確認

#### Step 10: romance/intimacy カテゴリ 4 種実装
- `masked_longing.j2`, `deflected_confession.j2`, `teasing_as_shield.j2`, `silent_understanding.j2`
- 親密度・秘密共有度で使い分け
- **テスト**: `test_templates_romance.py` - 親密度パラメータ別出力確認

#### Step 11: comedy/deflection カテゴリ 3 種実装
- `self_deprecating_deflection.j2`, `absurdist_redirect.j2`, `deadpan_evade.j2`
- 緊張緩和・話題逸らし・自虐で本音隠蔽
- **テスト**: `test_templates_comedy.py` - トーン確認・不適切ギャグ防止

#### Step 12: action/physical カテゴリ 3 種実装（台詞なし・動作のみ）
- `meaningful_glance.j2`, `symbolic_gesture.j2`, `environmental_interaction.j2`
- 「沈黙そのもの」をテンプレート化
- **テスト**: `test_templates_action.py` - 台詞ゼロ・動作のみ出力確認

#### Step 13: 共通変数・ビート辞書の標準化・外部化
- `data/subtext/beats.yaml`, `actions.yaml`, `irony_phrases.yaml` 作成
- テンプレートから `{{ beats.pause }}` 等で参照
- 作家が YAML 編集のみで語彙拡張可能
- **テスト**: `test_shared_data.py` - 辞書網羅性・重複なし・カテゴリ分類確認

#### Step 14: テンプレート品質ゲート・自動検証
- 必須チェック：台詞行数≤2、ト書き≥1、変数未使用なし、文字数上限
- `scripts/validate_templates.py` で CI 実行
- **テスト**: `test_template_validation.py` - 違反テンプレート検知・修正ガイド表示

---

### Phase 3: 選択ロジック高度化・統合（Step 15-20）

#### Step 15: 会話履歴・関係性グラフ参照機能
- `SubtextContext` に `history_summary`, `relationship_graph` 追加
- 直前 3 発話のテンプレート ID・感情傾向で重複回避・エスカレーション制御
- **テスト**: `test_history_aware_selection.py` - 連続同テンプレ回避・感情曲線整合確認

#### Step 16: キャラクター別テンプレート制約・方言・口調対応
- `character_profiles.yaml` に `preferred_templates`, `forbidden_tags`, `dialect_rules`
- レンダリング後フィルタで口調変換（敬語→タメ口等）
- **テスト**: `test_character_constraints.py` - プロファイル適用・禁則タグ除外・方言変換確認

#### Step 17: シーン・ジャンル・トーン別重み調整
- `scene_context.yaml` で `genre_weights`, `tone_modifiers` 定義
- ホラー×裏切り→ `weight * 1.5`、コメディ×悲嘆→ `weight * 0.3` 等
- **テスト**: `test_scene_weighting.py` - ジャンル別選択傾向・極端な重み変化確認

#### Step 18: フォールバックチェーン・デフォルトテンプレート
- マッチゼロ時：`generic_subtext.j2` → `minimal_beat.j2` → ハードコードビート
- ログにフォールバック理由記録
- **テスト**: `test_fallback_chain.py` - 各段階フォールバック発火・ログ確認

#### Step 19: 既存生成パイプライン統合・A/B 切替
- `GenerationPipeline` に `subtext_mode: "template|rule|hybrid|off"` 追加
- 設定ファイル・環境変数で切替
- **テスト**: `test_pipeline_integration.py` - 全モード動作・切替即時反映確認

#### Step 20: 作家向けテンプレートエディタ用 API 基盤
- `GET/POST/PUT/DELETE /subtext/templates`
- バリデーション・プレビュー・差分表示・バージョン履歴
- **テスト**: `test_template_api.py` - CRUD・プレビュー・権限・競合防止確認

---

### Phase 4: 品質保証・運用・拡張（Step 21-24）

#### Step 21: 黄金サンプル・ビジュアル回帰テスト
- `tests/golden/templates/` に 入力コンテキスト + 期待出力構造 ペア 50 件
- レンダリング結果の構造的等価性検証（台詞文字列は fuzzy 一致）
- **テスト**: `test_golden_templates.py` - 全サンプルパス・差分レポート出力

#### Step 22: テンプレート使用統計・ヒートマップ生成
- 適用テンプレート ID・コンテキスト・頻度を集計
- `scripts/generate_template_heatmap.py` → `reports/template_usage.html`
- 未使用・低使用テンプレートの見直し支援
- **テスト**: `test_usage_stats.py` - 集計正確性・レポート生成確認

#### Step 23: 多言語対応・i18n 基盤
- テンプレート ID 共通・言語別ディレクトリ `templates/subtext/{ja,en,zh}/`
- 変数名・ビート辞書も言語別
- **テスト**: `test_i18n.py` - 言語切替・フォールバック・変数整合確認

#### Step 24: 統合テスト・ドキュメント・リリース
- 全ステップ統合・カバレッジ測定
- `docs/subtext_templates.md`: 作家向けテンプレート作成ガイド・ベストプラクティス
- リリースチェックリスト・タグ付け
- **テスト**: フルテストスイート・カバレッジ 90% 以上・ドキュメント例実行確認

---

## 実装順序の依存関係

```mermaid
graph TD
    1 --> 2 --> 3 --> 4 --> 5 --> 6
    6 --> 7 --> 8 --> 9 --> 10 --> 11 --> 12 --> 13 --> 14
    14 --> 15 --> 16 --> 17 --> 18 --> 19 --> 20
    20 --> 21 --> 22 --> 23 --> 24
```

## 完了基準
- [ ] 全カテゴリ計 23 テンプレート実装・検証済み
- [ ] 黄金サンプル 50 件で構造的回帰なし
- [ ] コンテキストマッチング精度 95% 以上（手動評価）
- [ ] 作家が YAML 編集のみで語彙・テンプレ追加可能
- [ ] カバレッジ 90% 以上

## リスクと対策
| リスク | 対策 |
|---|---|
| テンプレート増加で選択ロジック複雑化 | タグ・重み・final フラグで明示制御、可視化ツール整備 |
| 作家が破壊的変更を加える | API 側でバリデーション・プレビュー必須・バージョン管理 |
| 言語間でニュアンス崩壊 | 翻訳メモリ・用語集連携、ネイティブチェックフロー整備 |
| 実行時オーバーヘッド | インデックスキャッシュ・テンプレートプリコンパイル・遅延読み込み |