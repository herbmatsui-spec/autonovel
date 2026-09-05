# 改善案 1: 反AI検出 → 修正ループ 実装計画書

## 概要

`StyleAuditor` を拡張し、LLM ベースの「AI 味検出器」(`AntiAIDetector`) を新規追加して、執筆 Draft から AI 生成痕迹を除去する自動修正ループを実装する。低性能な LLM（ローカル LLM、CPU 推論、gemma-2-2b 等）でも安定動作するように、ルールベース検出を主体とし、LLM は最小限のサニティチェックと代替表現提案のみに使用する。

## 全体アーキテクチャ

```
WritingAgent.generate_draft()
    │
    ▼
StyleAuditor (既存) ──────▶ score < style_threshold
    │                              │
    ▼                              ▼
AntiAIDetector (新規) ◀── 既存SpecialistAuditor ベースを継承
    │
    ├─ Step A: ルールベース7カテゴリ検出（LLM非依存）
    ├─ Step B: LLMサニティチェック（低コスト・短文のみ）
    ├─ Step C: 違反箇所の自動修正（LLM or ルール置換）
    │
    ▼
修正後テキスト → StyleAuditor に再注入
    │
    ▼
反復上限 (max_correction_loops) までループ
    │
    ▼
最終テキスト → EpisodePipeline へ
```

## 低性能 LLM 対応方針

1. **ルールベース検出を主体にする**: 7カテゴリ全てを正規表現・統計的手法だけで実装
2. **LLM はオプション**: 環境変数 `ANTI_AI_LLM_ENABLED=false` で完全にルールベース動作
3. **短文のみ LLM に渡す**: 2000文字チャンクに分割し、各チャンクで独立検出
4. **キャッシュ活用**: 同一テキストの検出結果は SQLite/MemoryCache で再利用
5. **レート制限**: LLM 呼び出しは最大3回/チャプター、合計トークン 1000 以内

---

## Phase 0: 事前準備（ステップ 1〜6）

### Step 1: 実装計画書レビュー & 既存コードの精査
- `src/agents/specialists/style_auditor.py` を読んで既存ロジックを理解
- `src/agents/specialist_auditor_base.py` のインターフェースを確認
- `src/services/audit_aggregator.py` の統合パターンを確認
- 既存 `DeAIAuditor` (`src/agents/audit.py:722`) との違いを明確化
- 想定工数: 30分

### Step 2: 設定ファイル構造の決定
- `config/anti_ai_config.yaml` を新規作成するディレクトリパスを決定
- 既存 `config/audit_weights.yaml` の構造に合わせる
- 想定工数: 15分

### Step 3: データモデル設計（机上）
- `AntiAIDetectionResult` dataclass のフィールドを定義
  - `category_scores: dict[str, float]`
  - `total_score: float`
  - `violations: list[ViolationSpan]`
  - `method: Literal["rule_based", "llm", "hybrid"]`
- `ViolationSpan` を定義（start, end, category, severity, suggestion）
- 想定工数: 30分

### Step 4: 7カテゴリのルールベース判定ロジック設計
- 各カテゴリの正規表現パターン辞書を作成（机上）
- 入力: テキスト, 出力: カテゴリ毎のヒット箇所リスト
- 想定工数: 45分

### Step 5: 修正戦略の決定
- 「置換」「言い換え」「削除」の3パターンを用意
- 修正レベル（CRITICAL/HIGH/MEDIUM/LOW）を定義
- 想定工数: 20分

### Step 6: 開発ブランチの作成
- `git checkout -b feature/anti-ai-detection`
- `.git/COMMIT_EDITMSG` 等の状態確認
- 想定工数: 5分

---

## Phase 1: 設定・定数定義（ステップ 7〜12）

### Step 7: 設定 YAML ファイル作成
- `config/anti_ai_config.yaml` を作成
- 7カテゴリの有効/無効フラグ
- 閾値設定
- 想定工数: 20分

### Step 8: 設定ローダーの作成
- `src/config/anti_ai_config.py` を作成
- Pydantic ベースの `AntiAIConfig` モデル定義
- YAML 読み込み関数 `load_anti_ai_config()`
- 想定工数: 30分

### Step 9: 設定デフォルト値定義
- 7カテゴリのデフォルト閾値（重み・スコア上限）設定
- 想定工数: 15分

### Step 10: 環境変数サポート追加
- `ANTI_AI_LLM_ENABLED` (default: false)
- `ANTI_AI_MAX_LOOPS` (default: 2)
- `ANTI_AI_THRESHOLD` (default: 70.0)
- 想定工数: 20分

### Step 11: 設定テストのセットアップ
- `tests/unit/test_anti_ai_config.py` を作成
- デフォルト値のロードテスト
- 想定工数: 30分

### Step 12: 既存テストの実行（ベースライン）
- `pytest tests/unit/test_specialist_auditors.py -v` 実行
- 全テストパスを確認
- 想定工数: 10分

---

## Phase 2: データモデル実装（ステップ 13〜20）

### Step 13: `ViolationSpan` データクラス作成
- `src/services/anti_ai/__init__.py` パッケージ作成
- `src/services/anti_ai/models.py` に dataclass 定義
- 想定工数: 20分

### Step 14: `Severity` Enum 定義
- `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` の4段階
- 想定工数: 10分

### Step 15: `AICategory` Enum 定義
- 7カテゴリを Enum 化
  - TRANSITION_OVERUSE
  - SAME_STRUCTURE
  - DIRECT_EMOTION
  - HEDGING_PATTERNS
  - TEMPLATE_PHRASES
  - UNIFORM_PARAGRAPH
  - GENERIC_VOCABULARY
- 想定工数: 15分

### Step 16: `AntiAIDetectionResult` データクラス作成
- `category_scores: dict[AICategory, float]`
- `total_score: float` (0-100、100=クリーン)
- `violations: list[ViolationSpan]`
- `method: str`
- `to_dict()` メソッド
- 想定工数: 30分

### Step 17: スコア正規化ヘルパー実装
- 100点満点換算ロジック
- カテゴリ別重み適用
- 想定工数: 20分

### Step 18: データモデル単体テスト作成
- `tests/unit/anti_ai/test_models.py`
- スコア計算の境界値テスト
- 想定工数: 30分

### Step 19: データモデルテスト実行 & 修正
- `pytest tests/unit/anti_ai/test_models.py -v`
- 想定工数: 15分

### Step 20: フィクスチャ作成
- `tests/fixtures/anti_ai_samples.py` に検出用サンプルテキスト
  - クリーンなテキスト
  - TRANSITION_OVERUSE 違反
  - SAME_STRUCTURE 違反
  - DIRECT_EMOTION 違反
  - 混合違反
- 想定工数: 30分

---

## Phase 3: ルールベース検出ロジック実装（ステップ 21〜35）

### Step 21: ルールベース検出器基底クラス作成
- `src/services/anti_ai/rule_detector.py` に `BaseRuleDetector` 抽象クラス
- `detect(text) -> list[ViolationSpan]` メソッド
- 想定工数: 30分

### Step 22: カテゴリ1 - TRANSITION_OVERUSE 検出器
- 対象パターン: しかし/さらに/また/なお/ところで
- 文中の密度計算（3文に1回以上で違反）
- 想定工数: 45分

### Step 23: カテゴリ2 - SAME_STRUCTURE 検出器
- 「〜だった。〜だった。〜だった。」の3連続検出
- 同一語尾の反復検出
- 想定工数: 45分

### Step 24: カテゴリ3 - DIRECT_EMOTION 検出器
- 「〜と思った」「〜と感じた」等の直接的內面描写
- 段落内2回以上で違反
- 想定工数: 45分

### Step 25: カテゴリ4 - HEDGING_PATTERNS 検出器
- 「〜かもしれません」「〜そらく」「〜と考えられます」
- 想定工数: 30分

### Step 26: カテゴリ5 - TEMPLATE_PHRASES 検出器
- 「重要なことに」「注目すべきは」「結論として」
- 想定工数: 30分

### Step 27: カテゴリ6 - UNIFORM_PARAGRAPH 検出器
- 段落長 ±5文字差で3連続を検出
- 想定工数: 45分

### Step 28: カテゴリ7 - GENERIC_VOCABULARY 検出器
- 抽象語（素晴らしい/興味深い/多様な）5回/千文字で違反
- 想定工数: 30分

### Step 29: 全検出器のレジストリ登録
- `src/services/anti_ai/rule_detector.py` に `RULE_DETECTORS` dict 追加
- カテゴリ→検出器のマッピング
- 想定工数: 20分

### Step 30: ルールベース統合オーケストレータ
- `RuleBasedAntiAIDetector` クラス
- 全カテゴリ並列実行（asyncio.gather）
- 結果集約
- 想定工数: 45分

### Step 31: ルールベース検出器単体テスト
- `tests/unit/anti_ai/test_rule_detectors.py`
- 各カテゴリ毎の正常系・異常系
- 想定工数: 60分

### Step 32: フィクスチャを使った結合テスト
- `tests/unit/anti_ai/test_rule_detector_integration.py`
- 想定工数: 30分

### Step 33: エッジケース対応
- 短文（100文字未満）対応
- 改行・空白のみのテキスト対応
- 想定工数: 30分

### Step 34: パフォーマンス計測
- 5000文字テキストでの処理時間測定
- 目標: 100ms 以内
- 想定工数: 30分

### Step 35: ルールベース全テスト実行 & 修正
- `pytest tests/unit/anti_ai/ -v`
- 想定工数: 30分

---

## Phase 4: 修正ロジック実装（ステップ 36〜48）

### Step 36: 修正戦略インターフェース定義
- `src/services/anti_ai/corrector.py` 作成
- `BaseCorrector` 抽象クラス
- `correct(text, violations) -> CorrectedText`
- 想定工数: 30分

### Step 37: ルール置換型修正器（TRANSITION_OVERUSE）
- 過度な接続詞を削除または別表現に置換
- 想定工数: 45分

### Step 38: ルール置換型修正器（SAME_STRUCTURE）
- 同一構文の分散化
- 文末表現のバリエーション置換辞書
- 想定工数: 60分

### Step 39: ルール置換型修正器（DIRECT_EMOTION）
- 「〜と思った」→ 五感描写への置換辞書
- 想定工数: 45分

### Step 40: ルール置換型修正器（HEDGING_PATTERNS）
- 曖昧表現の断定化
- 想定工数: 30分

### Step 41: ルール置換型修正器（TEMPLATE_PHRASES）
- 論文調の口語化
- 想定工数: 30分

### Step 42: 構造修正器（UNIFORM_PARAGRAPH）
- 段落の結合・分割
- 想定工数: 45分

### Step 43: 語彙置換修正器（GENERIC_VOCABULARY）
- 抽象語の具体語置換辞書
- 想定工数: 30分

### Step 44: 修正器レジストリ
- 全修正器を `CORRECTORS` dict に登録
- 想定工数: 20分

### Step 45: 修正パイプライン実装
- `AntiAICorrector` クラス
- 違反を優先度順に処理
- 想定工数: 45分

### Step 46: 修正ロジック単体テスト
- `tests/unit/anti_ai/test_corrector.py`
- 想定工数: 60分

### Step 47: 修正後のスコア改善検証テスト
- 修正前スコア < 修正後スコア を確認
- 想定工数: 30分

### Step 48: 修正パイプライン統合テスト
- `tests/unit/anti_ai/test_correction_pipeline.py`
- 想定工数: 30分

---

## Phase 5: AntiAIDetector 実装（ステップ 49〜55）

### Step 49: AntiAIDetector クラス骨格
- `src/agents/specialists/anti_ai_detector.py` 作成
- `SpecialistAuditor` を継承
- `specialist_name = "anti_ai"` 設定
- 想定工数: 30分

### Step 50: `audit()` メソッド実装
- ルールベース検出実行
- スコア計算
- `SpecialistAuditResult` で返却
- 想定工数: 45分

### Step 51: `_fallback()` 実装
- LLM 無効時のフォールバック
- 想定工数: 20分

### Step 52: LLM サニティチェック機能（オプション）
- `enable_llm=True` 時のみ動作
- 短文チャンク分割 + LLM 検証
- トークン数制限
- 想定工数: 60分

### Step 53: 既存 StyleAuditor との統合
- `StyleAuditor` に `anti_ai_score` 反映ロジック追加
- 想定工数: 30分

### Step 54: 単体テスト作成
- `tests/unit/anti_ai/test_anti_ai_detector.py`
- 既存 `test_specialist_auditors.py` のスタイルを踏襲
- 想定工数: 60分

### Step 55: AuditAggregator への登録
- `src/agents/specialists/__init__.py` に `AntiAIDetector` 追加
- `audit_weights.yaml` の `anti_ai` キーを追加（必要に応じて）
- 想定工数: 20分

---

## Phase 6: 修正ループ実装（ステップ 56〜65）

### Step 56: 修正ループコントローラ作成
- `src/services/anti_ai/loop_controller.py` 作成
- `AntiAILoopController` クラス
- 想定工数: 30分

### Step 57: ループ制御ロジック実装
- スコア閾値チェック
- 最大ループ数管理
- 早期終了条件
- 想定工数: 45分

### Step 58: 修正履歴トラッキング
- `CorrectionHistory` データクラス
- イテレーション毎のスコア・違反数・修正数の記録
- 想定工数: 30分

### Step 59: ループ実行メソッド実装
- `async def run(text, max_loops, threshold) -> FinalResult`
- 想定工数: 45分

### Step 60: 早期終了条件実装
- スコアが閾値超過で終了
- 違反ゼロで終了
- スコア改善なしで終了
- 想定工数: 30分

### Step 61: ループバックオフ実装
- 連続失敗時の待機
- 指数バックオフ
- 想定工数: 30分

### Step 62: ループコントローラ単体テスト
- `tests/unit/anti_ai/test_loop_controller.py`
- 想定工数: 45分

### Step 63: ループの統合テスト
- フィクスチャ使用
- 3回ループで改善することを確認
- 想定工数: 30分

### Step 64: メトリクス追加
- `anti_ai_detection_total` (Prometheus)
- `anti_ai_corrections_total`
- `anti_ai_loop_iterations`
- 想定工数: 30分

### Step 65: 設定駆動のループパラメータ化
- `config/anti_ai_config.yaml` から閾値・ループ数読み込み
- 想定工数: 20分

---

## Phase 7: 統合・配線（ステップ 66〜69）

### Step 66: WritingService への組み込み
- `src/services/writing_service.py` の `generate_with_quality_assurance()` に修正ループ追加
- `regeneration_focus="anti_ai_correction"` 設定
- 想定工数: 60分

### Step 67: EpisodePipeline への組み込み
- `src/agents/episode_pipeline.py` の Draft 生成後に `AntiAILoopController` 呼び出し
- 想定工数: 45分

### Step 68: 管理画面 API 追加
- `src/backend/routers/anti_ai.py` 新規
- `POST /admin/anti_ai/detect` (テキスト→スコア)
- `POST /admin/anti_ai/correct` (テキスト→修正後)
- `GET /admin/anti_ai/config` (設定取得)
- 想定工数: 60分

### Step 69: 設定駆動の有効/無効フラグ
- `ENABLE_ANTI_AI_LOOP` 環境変数
- false 時はループ完全スキップ
- 想定工数: 20分

---

## Phase 8: 検証・ドキュメント（ステップ 70〜72）

### Step 70: E2E 統合テスト
- `tests/e2e/test_anti_ai_full_flow.py` 作成
- かんたんモード起動 → Draft 生成 → 修正ループ → 最終出力まで
- 想定工数: 90分

### Step 71: ドキュメント整備
- `docs/anti_ai_detection.md` 作成
- 各カテゴリの説明と閾値の根拠
- 運用ガイド
- 想定工数: 60分

### Step 72: 全体テスト実行 & PR 作成
- `pytest tests/ -v --cov=src/services/anti_ai`
- 既存テスト全パスを確認
- パフォーマンス回帰チェック
- `git commit` & `git push`
- 想定工数: 45分

---

## 全体工数見積もり

| Phase | ステップ範囲 | 工数 |
|-------|------------|------|
| Phase 0: 事前準備 | 1-6 | 約2.5時間 |
| Phase 1: 設定・定数 | 7-12 | 約2時間 |
| Phase 2: データモデル | 13-20 | 約3時間 |
| Phase 3: ルールベース検出 | 21-35 | 約9時間 |
| Phase 4: 修正ロジック | 36-48 | 約8時間 |
| Phase 5: Detector 実装 | 49-55 | 約4.5時間 |
| Phase 6: 修正ループ | 56-65 | 約5時間 |
| Phase 7: 統合・配線 | 66-69 | 約3時間 |
| Phase 8: 検証・ドキュメント | 70-72 | 約3時間 |
| **合計** | **1-72** | **約40時間** |

## リスクと対策

| リスク | 対策 |
|--------|------|
| ルールベースで誤検出が多い | フィクスチャによる境界値テスト充実、フィードバックループでチューニング |
| LLM 呼び出しが高コスト | 環境変数で完全無効化可能、短文チャンク化、キャッシュ |
| 既存テストへの影響 | Phase 1 で `audit_weights.yaml` の `anti_ai` キーをオプショナルにし、デフォルト無効 |
| パフォーマンス回帰 | Phase 3 Step 34 で計測、目標100ms/5000文字 |

## 次のステップ

この計画書が承認されたら、Step 1 から開始する。
