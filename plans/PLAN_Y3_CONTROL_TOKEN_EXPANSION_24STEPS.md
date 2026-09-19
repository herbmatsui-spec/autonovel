# PLAN_Y3: 生成時コントロールトークン埋め込み・後処理展開実装計画（24ステップ）

## 概要
初回生成プロンプトに特殊トークンを仕込み、LLM に「サブテキスト指示」を出力させる。後処理（単一パス正規表現置換）でトークンを展開。LLM 追加呼び出しゼロ。

## 前提
- 既存プロンプトテンプレート（Jinja2）にトークン指示を追記可能
- 後処理は生成直後のテキストに対し 1 回実行
- トークン辞書は YAML で外部管理・作家編集可能

---

## ステップ一覧

### Phase 1: トークン仕様・辞書・プロンプト統合（Step 1-6）

#### Step 1: トークン仕様策定・BNF 定義
```
TOKEN := "[" CATEGORY ":" KEY [":" MODIFIER]* "]"
CATEGORY := "SUBTEXT" | "BEAT" | "ACTION" | "GLANCE" | "PAUSE" | "IRONY" | "INTERNAL"
KEY := [a-z_]+
MODIFIER := [a-z_]+
例:
  [SUBTEXT:irony]
  [BEAT:pause:long]
  [ACTION:hide_hands:trembling]
  [GLANCE:away:down]
  [PAUSE:breath]
  [IRONY:cold_acceptance]
  [INTERNAL:suppressed_rage]
```
- **テスト**: `test_token_spec.py` - 正規表現パーサー・妥当/不妥当ケース網羅

#### Step 2: トークン辞書 YAML 設計・初期データ作成
```yaml
# data/subtext/tokens.yaml
subtext:
  irony:
    templates:
      - "「……{phrase}」"
      - "「……{phrase}——{beat}」"
    phrases: ["そう。好きにすればいいわ", "君に何が分かる", "期待しないことにする"]
    weights: [0.5, 0.3, 0.2]
  cold_acceptance:
    templates: ["「……{phrase}」——{action}"]
    phrases: ["そう。好きにすれば", "ああ、それでいい"]
    actions: ["乾いた笑みをこぼしながら、震える指先をマントの奥へ隠した", "視線を落とし、杯を静かに置いた"]

beat:
  pause:
    short: ["……", "一瞬、間が開く", "静寂が張り詰める"]
    long: ["長い沈黙が流れる", "数秒、何も言葉が返ってこない"]
  breath: ["深く息を吐く", "吐息を漏らす"]

action:
  hide_hands:
    trembling: ["震える指先をマントの奥へ隠した", "拳を握りしめ、袖の中に押し込んだ"]
    calm: ["指先を袖で拭う", "手を膝の上で組み直した"]
  glance_away:
    down: ["視線を落とす", "伏し目がちになる"]
    side: ["視線を逸らす", "横を向く"]
```
- **テスト**: `test_token_dict.py` - YAML 読み込み・スキーマ検証・重複キー検知

#### Step 3: プロンプトテンプレートへのトークン指示埋め込み
- `prompts/templates/narrative/dialogue_generation.j2` に追記:
```jinja2
{# サブテキスト指示 #}
以下のトークンを台詞に埋め込み、サブテキストを表現せよ：
- [SUBTEXT:irony] - 本音と逆の皮肉を言う
- [BEAT:pause] - 重要な感情の直前に沈黙を入れる
- [ACTION:hide_hands] - 震える手を隠す動作を入れる
- [GLANCE:away] - 視線を逸らす
- [IRONY:cold_acceptance] - 冷ややかな受容を示す
トークンは台詞行の前後、または台詞内に自然に配置せよ。
```
- **テスト**: `test_prompt_integration.py` - プロンプトレンダリング・トークン指示含有確認

#### Step 4: トークンパーサー・展開エンジン実装
- `TokenExpander` クラス：
  - 辞書読み込み・キャッシュ
  - `expand(text: str, context: dict, seed: int) -> str`
  - 正規表現 `r'\[(\w+):([^\]]+)\]'` でマッチ → カテゴリ/キー/修飾子分解 → 辞書からテンプレート選択 → 変数展開
  - 変数: `{phrase}`, `{beat}`, `{action}`, `{speaker}`, `{emotion}` 等
- **テスト**: `test_token_expander.py` - 全トークン種別・修飾子・変数展開・未定義キー挙動

#### Step 5: 確率的選択・シード固定・再現性確保
- `random.Random(seed)` 使用、シード = `hash(context.scene_id + context.turn_index)`
- 重み付き選択・シャッフル再現性
- **テスト**: `test_deterministic_expansion.py` - 同一コンテキストで同一出力・異なるコンテキストで分散確認

#### Step 6: ネストトークン・再帰展開対応
- トークン展開結果にさらにトークン含む場合、最大 3 回まで再帰展開
- 循環検知・深度制限
- **テスト**: `test_nested_tokens.py` - ネスト・循環・深度制限動作確認

---

### Phase 2: 後処理パイプライン・整形ルール（Step 7-14）

#### Step 7: 後処理パイプライン統合・実行順序定義
```python
def post_process_dialogue(raw: str, context: dict) -> str:
    text = TokenExpander.expand(raw, context)
    text = Formatter.normalize_punctuation(text)
    text = Formatter.ensure_beat_before_climax(text)
    text = Formatter.compress_explanatory_dialogue(text)
    text = Formatter.balance_dialogue_action_ratio(text)
    return text
```
- **テスト**: `test_pipeline_order.py` - 各段階の入出力・順序依存確認

#### Step 8: 整形ルール1 - 句読点・括弧・改行正規化
- 全角/半角統一、連続改行圧縮、台詞括弧統一（「」統一）
- **テスト**: `test_normalize_punctuation.py` - エッジケース網羅

#### Step 9: 整形ルール2 - クライマックス直前のビート強制挿入
- パターン: 感情語（爆発/崩壊/決意/覚悟/限界）直前の台詞末尾
- 挿入: `[BEAT:pause:long]` 展開済みビート
- **テスト**: `test_beat_before_climax.py` - 感情語バリエーション・挿入位置確認

#### Step 10: 整形ルール3 - 説明セリフ圧縮（3行以上→1行＋ビート）
- ルールエンジン（Y1）のルール1を簡易版で内包
- 正規表現ベース・設定で ON/OFF
- **テスト**: `test_compress_explanatory.py` - 3行/4行/混在ケース確認

#### Step 11: 整形ルール4 - 台詞:ト書き比率バランス調整
- 台詞行数 / (台詞行数 + ト書き行数) が 0.7 超ならト書き補強
- 補強用ビートプールからランダム挿入
- **テスト**: `test_balance_ratio.py` - 比率計算・補強挿入・上限確認

#### Step 12: 整形ルール5 - 同一話者連続台詞のマージ・ビート挟み
- 同一話者で台詞が連続 → 1行にマージ、間に `[BEAT:pause:short]` 挿入
- **テスト**: `test_merge_consecutive.py` - 連続数・話者切替境界確認

#### Step 13: 整形ルール6 - キャラクター口調後処理フィルタ
- `character_profiles.yaml` の `speech_patterns` で置換
- 例: `です・ます` → `だ・だね`、語尾 `わ・よ・ね` 付与
- **テスト**: `test_speech_filter.py` - プロファイル適用・過剰変換防止確認

#### Step 14: 整形ルール7-12 予約枠（拡張用）
- 空ステップ・テンプレートテスト自動生成
- **テスト**: テンプレートテスト雛形確認

---

### Phase 3: 統合・検証・デバッグ機能（Step 15-20）

#### Step 15: 既存生成フローへの統合・フック実装
- `GenerationPipeline._post_process_dialogue()` に組み込み
- 設定 `subtext.token_expansion.enabled: true` で制御
- **テスト**: `test_generation_integration.py` - エンドツーエンド・設定切替確認

#### Step 16: デバッグモード・トークン可視化・適用前後比較
- `debug: true` 時：トークンマーカー残し・展開前後 diff 出力
- HTML レポート生成（色分け表示）
- **テスト**: `test_debug_mode.py` - デバッグ出力形式・diff 正確性確認

#### Step 17: 黄金サンプル・回帰テストセット作成
- `tests/golden/token_expansion/` に 入力生成文 + コンテキスト + 期待出力 40 件
- プロンプト変更時も後処理のみで回帰検知可能
- **テスト**: `test_golden_token.py` - 全サンプルパス・CI 統合

#### Step 18: パフォーマンス測定・最適化
- 正規表現コンパイル済みキャッシュ・辞書メモリ常駐
- 1万行処理 50ms 以内目標
- **テスト**: `test_performance.py` - ベンチマーク・閾値確認

#### Step 19: エラーハンドリング・安全フォールバック
- 展開失敗 → 元テキスト返却・警告ログ・メトリクス記録
- 辞書欠落 → 組み込み最小辞書で動作
- **テスト**: `test_error_handling.py` - 各種障害注入・グレースフル動作確認

#### Step 20: 作家向けトークン辞書編集 UI 用 API
- `GET/PUT /subtext/tokens` （YAML 丸ごと・部分配置）
- バリデーション・プレビュー（サンプルコンテキストで展開結果表示）
- **テスト**: `test_token_api.py` - CRUD・バリデーション・プレビュー確認

---

### Phase 4: 品質強化・多言語・リリース（Step 21-24）

#### Step 21: トークン使用統計・カバレッジレポート
- 使用トークン種別・頻度・未使用キー検出
- `scripts/token_usage_report.py` → CI アーティファクト
- **テスト**: `test_usage_report.py` - 集計正確性・レポート形式確認

#### Step 22: 多言語トークン辞書・言語別展開対応
- `tokens.{ja,en,zh}.yaml` 切替
- 言語共通キー・言語固有テンプレート両対応
- **テスト**: `test_multilingual_tokens.py` - 言語切替・フォールバック・キー整合確認

#### Step 23: プロンプト・トークン辞書の共進化ワークフロー
- プロンプト指示トークンセットと辞書キーの整合性チェック
- `scripts/validate_prompt_tokens.py` で CI 検証
- **テスト**: `test_prompt_token_sync.py` - 不整合検知・修正ガイド表示

#### Step 24: 統合テスト・ドキュメント・リリース
- 全ステップ統合・カバレッジ測定
- `docs/subtext_tokens.md`: トークン設計指針・辞書編集ガイド・プロンプト連携手順
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
- [ ] トークン種別 7 カテゴリ・辞書エントリ 100 以上実装
- [ ] 黄金サンプル 40 件で回帰なし
- [ ] 後処理単体 50ms/1万行以内
- [ ] プロンプト変更に追従（トークン指示追加のみで新表現対応可能）
- [ ] カバレッジ 90% 以上

## リスクと対策
| リスク | 対策 |
|---|---|
| LLM がトークンを出力しない/誤出力 | プロンプトに few-shot 例追加・後処理で未展開トークン除去・メトリクス監視 |
| トークン展開で不自然な日本語になる | テンプレートに助詞・語尾調整ロジック・作家レビューフロー |
| 辞書肥大化で選択品質低下 | タグ・重み・使用統計で整理・定期レビュー |
| プロンプトと辞書の乖離 | CI で整合性チェック・共通定義ファイルから両方生成 |

---

## 3アプローチ併用時の統合ポイント（参考）

| 統合箇所 | Y1 ルール | Y2 テンプレート | Y3 トークン |
|---|---|---|---|
| 実行順序 | 3番目（最終整形） | 2番目（文脈選択） | 1番目（生成直後展開） |
| 入力 | Y3出力 | Y3出力 | 生LLM出力 |
| 出力 | 確定テキスト | 構造化ダイアログ | トークン展開済みテキスト |
| 無効化 | `final` フラグ | `final` フラグ | トークンなしでスキップ |