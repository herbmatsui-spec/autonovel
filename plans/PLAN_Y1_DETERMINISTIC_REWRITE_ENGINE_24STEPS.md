# PLAN_Y1: 決定論的リライト・ルールエンジン実装計画（24ステップ）

## 概要
LLM呼び出しなしで、正規表現ベースのルールエンジンにより「サブテキストと沈黙」を強制適用する。生成直後・保存前・エクスポート時のいずれか1回実行。

## 前提
- Python 3.10+ 環境
- 既存の生成パイプラインに `post_process` フックがある想定
- テストは `pytest`、カバレッジ 90% 以上目標

---

## ステップ一覧

### Phase 1: 基盤構築（Step 1-6）

#### Step 1: プロジェクト構造とルールエンジン雛形作成
- `src/narrative/subtext_engine/` ディレクトリ作成
- `__init__.py`, `rules.py`, `engine.py`, `models.py` 作成
- **テスト**: `tests/narrative/subtext_engine/test_engine_smoke.py` - インポート・初期化のみ確認

#### Step 2: データモデル定義
- `models.py` に `DialogueBlock`, `RewriteRule`, `RewriteResult`, `SubtextContext` 定義
- `DialogueBlock`: speaker, lines[], context(dict)
- **テスト**: `test_models.py` - 型ヒント・シリアライズ確認

#### Step 3: ルール基底クラスとレジストリ実装
- `RuleBase` 抽象基底クラス（`apply(block) -> RewriteResult`）
- `RuleRegistry` シングルトン（登録・優先度ソート・取得）
- **テスト**: `test_registry.py` - 登録・取得・優先度順序確認

#### Step 4: 正規表現ルール実装基盤
- `RegexRule(RuleBase)` 継承クラス作成
- パターン・置換関数・フラグ（`final`, `skip_if_matched`）保持
- **テスト**: `test_regex_rule.py` - 単一ルール適用・フラグ動作確認

#### Step 5: エンジン核心ロジック実装
- `SubtextEngine.process(blocks: list[DialogueBlock]) -> list[DialogueBlock]`
- ルール優先度順実行、`final` フラグで以降スキップ
- 変更履歴（`applied_rules`）記録
- **テスト**: `test_engine_core.py` - 複数ルール連結・履歴記録確認

#### Step 6: 設定ファイル駆動化
- `config/subtext_rules.yaml` にルール定義外出し
- YAML読み込み→`RegexRule`自動生成
- **テスト**: `test_config_load.py` - 設定読み込み・ルール生成確認

---

### Phase 2: コアルール実装（Step 7-14）

#### Step 7: ルール1 - 説明セリフ検出・圧縮（3行以上連続）
- パターン: `(?:「.+?」\n){3,}`
- 置換: 最後の1行残し、前をランダム「ト書き」に変換
- ト書きプール: `BEATS = ["沈黙が張り詰める", "視線を逸らす", "指先で杯を弄ぶ", "マントの裾を握りしめる", "深く息を吐く"]`
- **テスト**: `test_rule_explanatory_compress.py` - 3行/4行/5行ケース、境界値

#### Step 8: ルール2 - 感情直撃語の動作化置換
- 対象語: `悲し|怒っ|恨ん|悔し|寂し|腹立たし|ムカつ`
- 置換辞書: `{悲し: "悲しげな表情で、拳を握りしめ", 怒っ: "怒気を孕んだ瞳で、テーブルを叩く", ...}`
- **テスト**: `test_rule_emotion_to_action.py` - 全対象語・語尾変化・否定形除外確認

#### Step 9: ルール3 - 因果説明接続詞の皮肉・沈黙変換
- パターン: `(なぜなら|理由は|〜から|〜ため|ゆえに)(.+)`
- 置換: `……{group2}——{random_beat}` または皮肉定型文挿入
- 皮肉プール: `["そう。好きにすればいいわ", "君に何が分かる", "期待しないことにする"]`
- **テスト**: `test_rule_causal_to_irony.py` - 接続詞バリエーション・文末処理確認

#### Step 10: ルール4 - 「私は〜思う/感じる/信じる」主観表明の内在化
- パターン: `私は(.+?)(思う|感じる|信じて|確信し)ます?`
- 置換: ト書きのみ残す `——{group1}{group2}げな素振りを見せ`
- **テスト**: `test_rule_subjective_internalize.py` - 主語変化・丁寧語・砕け語対応

#### Step 11: ルール5 - 直接的な脅迫・宣言の含み持たせ変換
- パターン: `(殺す|潰す|復讐|後悔させ|許さない)(?:てやる|てみせる|ぞ)`
- 置換: `「……{random_cold_phrase}」——{threat_action}`
- 冷徹フレーズプール・脅迫アクションプール定義
- **テスト**: `test_rule_threat_subtext.py` - 暴力度合い別・性別話者別バリエーション

#### Step 12: ルール6 - 同意・従順セリフの皮肉・無言拒否化
- パターン: `(はい|わかりました|承知|従う|言う通り)(?:です|ました)?[。!]?`
- 置換: 確率分岐（皮肉 60% / 無言動作 40%）
- **テスト**: `test_rule_compliance_subvert.py` - 確率分布・シード固定で再現性確認

#### Step 13: ルール7 - 名前呼び・敬称の距離感演出
- パターン: `([君お前あなた]|[さん君ちゃん様])`
- 文脈（敵対/親密/公式）で呼称変更または削除→視線動作挿入
- **テスト**: `test_rule_address_distance.py` - コンテキスト別挙動・会話履歴参照確認

#### Step 14: ルール8-15 追加ルール実装（拡張枠）
- 空白ステップとして予約（将来のルール追加用）
- 各ステップで1ルール追加・テスト追加のテンプレート化
- **テスト**: テンプレートテスト自動生成スクリプト作成

---

### Phase 3: パイプライン統合・検証（Step 15-20）

#### Step 15: 既存生成パイプラインへのフック統合
- `src/pipeline/generation.py` 等に `post_process_hooks.append(subtext_engine.process)`
- 設定で ON/OFF 切替可能に
- **テスト**: `test_pipeline_integration.py` - エンドツーエンド生成→後処理確認

#### Step 16: 適用前後比較・ログ出力機能
- `debug_mode` 有効時：適用前/後/適用ルール一覧を JSONL 出力
- 差分可視化ヘルパー関数
- **テスト**: `test_debug_logging.py` - ログフォーマット・内容確認

#### Step 17: 黄金サンプル（ゴールデンセット）作成・回帰テスト
- `tests/golden/subtext_before_after/*.json` に Before/After ペア 30 件以上
- `test_golden_regression.py` - 全サンプルで現行エンジン出力が After と一致確認
- **テスト**: CI で毎回実行、差分検知時は FAIL

#### Step 18: パフォーマンスベンチマーク・閾値設定
- 1万ブロック処理で 100ms 以内目標
- `benchmarks/subtext_engine_bench.py` 作成
- CI で閾値超過時アラート
- **テスト**: `test_performance.py` - 閾値内確認

#### Step 19: 例外ハンドリング・フォールバック
- ルール適用中例外 → 元ブロック返却・警告ログ
- 設定読み込み失敗 → 組み込みデフォルトルールで動作
- **テスト**: `test_error_handling.py` - 各種例外注入・安全動作確認

#### Step 20: ドキュメント・運用ガイド作成
- `docs/subtext_engine.md`: ルール追加手順・デバッグ・黄金サンプル更新手順
- ルール設計指針（過剰変換防止・文脈保持・キャラクター声保持）
- **テスト**: ドキュメントリンク切れ・コード例実行確認

---

### Phase 4: 品質強化・拡張準備（Step 21-24）

#### Step 21: ルール競合検知・可視化ツール
- 同一ブロックに複数ルールがマッチした場合の警告
- `scripts/analyze_rule_conflicts.py` 作成
- **テスト**: `test_conflict_detection.py` - 故意に競合させ検知確認

#### Step 22: 統計レポート生成
- ルール別適用回数・削減文字数・ト書き挿入数を集計
- `SubtextEngine.generate_report() -> dict`
- **テスト**: `test_report_generation.py` - 集計正確性確認

#### Step 23: 作家向けルールカスタマイズ UI 用 API 追加
- `GET /subtext/rules`, `POST /subtext/rules` (CRUD)
- バリデーション・バージョン管理・ロールバック
- **テスト**: `test_rule_api.py` - CRUD・権限・バリデーション確認

#### Step 24: 統合テスト・リリース準備
- 全ステップ統合実行・カバレッジ測定
- `pytest --cov=src.narrative.subtext_engine --cov-report=term-missing`
- リリースチェックリスト確認・タグ付け
- **テスト**: フルテストスイート・カバレッジ 90% 以上確認

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
- [ ] 全 24 ステップのテストがパス
- [ ] 黄金サンプル 30 件以上で回帰なし
- [ ] パフォーマンス 100ms/1万ブロック以内
- [ ] カバレッジ 90% 以上
- [ ] ドキュメント完備・運用ガイド完成

## リスクと対策
| リスク | 対策 |
|---|---|
| ルール過剰適用でキャラ声崩壊 | `final` フラグ・キャラクター別除外リスト・黄金サンプルでガード |
| 正規表現の誤マッチ | 単体テスト網羅・境界値テスト・負例テスト必須 |
| 設定変更時の再起動不要化 | ファイル監視・ホットリロード実装（Step 23 で拡張） |