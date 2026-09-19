# PLAN_F0: グローバルナラティブバランサー アービトレーター統合層 実装計画（24ステップ）

## 概要
F1（DSPテンション）、F2（CSP制約）、F3（文法構造）の3バランサーを**並列実行**し、各々の検知結果・補正提案を**優先度付きアンサンブル**で統合・競合解決するオーケストレーション層。単一エントリーポイント `GlobalNarrativeBalancer` を提供。

**入力**: `PlotState`（ビート列・キャラ弧・伏線DB・現在話数）  
**出力**: `BalancedPlotState`（統合補正適用済みプロット状態）

---

## ステップ定義

### Phase 0: 共通インターフェース・データ契約 (1-4)

#### Step 1: 統合データモデル定義
- **ファイル**: `src/narrative_balancer/arbitrator/models.py`
- **内容**: 
  - `PlotState` - 全バランサー共通入力（ビート列、キャラ状態、伏線状態、メタデータ）
  - `BalancerResult` - 共通出力インターフェース（`detections`, `corrections`, `confidence`, `metadata`）
  - `Detection` - 検知情報（`type`, `severity`, `episode_range`, `evidence`, `source_balancer`）
  - `Correction` - 補正アクション（`action_type`, `target_episodes`, `payload`, `priority`, `rationale`）
  - `BalancedPlotState` - 最終出力
- **テスト**: `tests/unit/test_arbitrator_models.py` - シリアライズ・スキーマ検証

#### Step 2: バランサーポート（Protocol）定義
- **ファイル**: `src/narrative_balancer/arbitrator/ports.py`
- **プロトコル**: `NarrativeBalancer` - `analyze(state) -> BalancerResult`, `correct(state) -> BalancerResult`
- **実装確認**: F1/F2/F3 の各メインクラスがこのプロトコルを満たすこと（構造的部分型）
- **テスト**: `tests/unit/test_balancer_port.py` - 3実装すべてで `isinstance(check)` パス確認

#### Step 3: 統合設定スキーマ
- **ファイル**: `config/arbitrator.yaml`
- **内容**:
  - `balancers`: 各バランサーの有効/無効、設定ファイルパス、重み
  - `arbitration`: `priority_order`, `conflict_resolution`, `min_consensus`
  - `execution`: `parallel`, `timeout_ms`, `fallback_chain`
  - `output`: `merge_strategy`, `audit_log_enabled`
- **テスト**: `tests/unit/test_arbitrator_config.py` - バリデーション・デフォルト値

#### Step 4: ファクトリ・レジストリ
- **ファイル**: `src/narrative_balancer/arbitrator/factory.py`
- **クラス**: `BalancerRegistry` - 名前→インスタンスマッピング、設定から遅延初期化
- **関数**: `create_balancer(name, config) -> NarrativeBalancer`, `create_all(config) -> Dict[str, NarrativeBalancer]`
- **テスト**: `tests/unit/test_factory.py` - 3バランサー正常生成・設定注入確認

---

### Phase 1: 並列実行基盤 (5-8)

#### Step 5: 非同期実行エンジン
- **ファイル**: `src/narrative_balancer/arbitrator/executor.py`
- **クラス**: `ParallelExecutor`
- **メソッド**: 
  - `run_analyze(state, balancers) -> Dict[str, BalancerResult]`
  - `run_correct(state, balancers) -> Dict[str, BalancerResult]`
- **実装**: `asyncio.gather` + `asyncio.wait_for`（タイムアウト保護）、例外時は部分結果返却
- **テスト**: `tests/unit/test_executor.py` - 正常/タイムアウト/例外/部分失敗ケース

#### Step 6: 実行メトリクス収集
- **ファイル**: `src/narrative_balancer/arbitrator/executor.py` (拡張)
- **追加**: 実行時間・メモリ・検知数・補正数を `ExecutionMetrics` として付与
- **テスト**: `tests/unit/test_executor_metrics.py` - メトリクスフィールド完全性確認

#### Step 7: フォールバックチェーン
- **ファイル**: `src/narrative_balancer/arbitrator/fallback.py`
- **ロジック**: 
  - 全成功 → 統合フェーズへ
  - 1つ失敗 → 残り2つで継続、失敗分は `fallback_result` で代替
  - 2つ失敗 → 残り1つの結果を単独採用、警告ログ
  - 全失敗 → 入力状態をそのまま返却、エラーフラグ立てる
- **テスト**: `tests/unit/test_fallback.py` - 全組み合わせシミュレーション

#### Step 8: 監査ログ・トレーサビリティ
- **ファイル**: `src/narrative_balancer/arbitrator/audit.py`
- **クラス**: `AuditLogger` - 構造化JSONL出力
- **記録**: 入力状態ハッシュ、各バランサー生結果、統合過程、最終決定理由
- **テスト**: `tests/unit/test_audit.py` - ログ完全性・再現性確認

---

### Phase 2: 競合解決・アンサンブル統合 (9-15)

#### Step 9: 検知結果正規化・マージ
- **ファイル**: `src/narrative_balancer/arbitrator/merge_detections.py`
- **関数**: `merge_detections(results: Dict[str, BalancerResult]) -> List[Detection]`
- **ロジック**: 
  - 同一話数・同一タイプ検知をグルーピング
  - `severity = max(severity_i * weight_i)` で重み付き最大値
  - `evidence` を結合（出典バランサー名付き）
  - `consensus_count` 記録（何バランサーが検知したか）
- **テスト**: `tests/unit/test_merge_detections.py` - 完全一致/部分一致/不一致ケース

#### Step 10: 補正アクション正規化・競合検出
- **ファイル**: `src/narrative_balancer/arbitrator/merge_corrections.py`
- **関数**: `merge_corrections(results) -> tuple[List[Correction], List[Conflict]]`
- **競合定義**: 同一話数に対する `action_type` または `payload` が矛盾
  - 例: DSP「テンション+3」、CSP「テンション-2」、文法「DISASTER挿入」
- **テスト**: `tests/unit/test_merge_corrections.py` - 競合/非競合ケース網羅

#### Step 11: 優先度ベース競合解決
- **ファイル**: `src/narrative_balancer/arbitrator/resolver.py`
- **クラス**: `PriorityResolver`
- **優先順位** (設定可、デフォルト):
  1. **Grammar (構造)** - ハード制約違反回避最優先
  2. **CSP (制約)** - 数値境界・キャラ弧・伏線整合性
  3. **DSP (信号)** - テンション曲線滑らかさ・単調化補正
- **アルゴリズム**: 競合グループごとに最高優先度アクション採用、次点は `superseded` フラグ
- **テスト**: `tests/unit/test_priority_resolver.py` - 全優先度順列で決定論的確認

#### Step 12: コンセンサス重み付け統合（代替戦略）
- **ファイル**: `src/narrative_balancer/arbitrator/consensus.py`
- **関数**: `consensus_merge(corrections, weights) -> List[Correction]`
- **ロジック**: 
  - 非競合は全採用
  - 競合時: `score = Σ(weight_i * confidence_i)` 最大のアクション採用
  - `min_consensus=2` 未満なら `HOLD` アクション（人間判断待ち）に変換
- **テスト**: `tests/unit/test_consensus.py` - 重み・信頼度変化で採用切替確認

#### Step 13: 統合戦略セレクター
- **ファイル**: `src/narrative_balancer/arbitrator/strategy.py`
- **クラス**: `MergeStrategy` (Enum: `PRIORITY`, `CONSENSUS`, `HYBRID`)
- **HYBRID**: 構造系(Grammar+CSP)はPRIORITY、信号系(DSP)はCONSENSUS
- **ファクトリ**: `create_strategy(config) -> MergeStrategy`
- **テスト**: `tests/unit/test_strategy.py` - 3戦略で同一入力→異なる出力確認

#### Step 14: 統合メイン関数
- **ファイル**: `src/narrative_balancer/arbitrator/integrator.py`
- **関数**: `integrate_results(raw_results, config) -> IntegratedResult`
- **フロー**: 
  1. 検知マージ → 2. 補正マージ+競合検出 → 3. 戦略選択 → 4. 解決 → 5. 適用順序ソート（話数順）
- **テスト**: `tests/integration/test_integrator.py` - 実データ近似でエンドツーエンド

#### Step 15: 補正適用エンジン（トランザクショナル）
- **ファイル**: `src/narrative_balancer/arbitrator/applier.py`
- **クラス**: `CorrectionApplier`
- **メソッド**: `apply(state: PlotState, corrections: List[Correction]) -> BalancedPlotState`
- **保証**: 
  - イミュータブル状態コピーで適用
  - 全適用成功 or 全ロールバック（アトミック）
  - 適用前後で `PlotState` 不変条件検証
- **テスト**: `tests/unit/test_applier.py` - 成功/部分失敗ロールバック/不変条件違反

---

### Phase 3: メインクラス・CLI・検証 (16-20)

#### Step 16: グローバルバランサーメインクラス
- **ファイル**: `src/narrative_balancer/arbitrator/balancer.py`
- **クラス**: `GlobalNarrativeBalancer`
- **メソッド**: 
  - `balance(state: PlotState) -> BalancedPlotState` (解析→統合→適用)
  - `analyze_only(state) -> IntegratedResult` (診断のみ)
  - `validate(state) -> ValidationReport` (全バランサー検証サマリ)
- **テスト**: `tests/integration/test_global_balancer.py` - 正常/中だるみ/破綻入力で期待動作

#### Step 17: CLI エントリーポイント
- **ファイル**: `src/narrative_balancer/arbitrator/cli.py`
- **コマンド**: 
  - `global-balance --state state.yaml --config arbitrator.yaml --output balanced.yaml`
  - `global-analyze --state state.yaml --report report.md`
  - `global-validate --state state.yaml --detail`
- **テスト**: `tests/integration/test_global_cli.py` - 3サブコマンド正常動作

#### Step 18: 統合ゴールデンマスタテスト
- **ファイル**: `tests/integration/test_global_golden.py`
- **フィクスチャ**: `tests/fixtures/global_golden/` - 15+ ケース
  - 正常40話、中だるみ(20-30話)、伏線腐敗、キャラ放置、複合破綻
  - 各ケース: 入力状態、期待出力状態、期待検知リスト、期待補正リスト
- **検証**: 状態ハッシュ比較、検知・補正の集合一致（順序不問）

#### Step 19: エンドツーエンドシナリオテスト
- **ファイル**: `tests/e2e/test_global_scenarios.py`
- **シナリオ**: 
  - `scenario_1_normal`: 正常進行→微細調整のみ
  - `scenario_2_midpoint_sag`: 第20話欠落→Grammar主導でDISASTER挿入
  - `scenario_3_tension_flat`: 第15-25話フラット→DSP主導でインパルス注入
  - `scenario_4_char_neglect`: 主人公敗北0、相棒未登場→CSP主導で制約修正
  - `scenario_5_complex`: 全問題混在→優先度順でGrammar→CSP→DSP適用
- **テスト**: 各シナリオで「期待される主要補正が含まれる」ことをアサート

#### Step 20: 回帰テストデータ自動生成スクリプト
- **ファイル**: `scripts/generate_global_regression.py`
- **機能**: 
  - ランダムプロット生成 → 3バランサー単体実行 → アービトレーター統合 → 結果保存
  - 既存フィクスチャとの差分検出
- **テスト**: `tests/meta/test_regression_generation.py` - スクリプト実行・出力妥当性

---

### Phase 4: 観測性・パフォーマンス・CI (21-24)

#### Step 21: 統合メトリクス・ダッシュボードデータ
- **ファイル**: `src/narrative_balancer/arbitrator/metrics.py`
- **クラス**: `GlobalMetrics` - Prometheus形式/JSON出力対応
- **指標**: 
  - `balancer_latency_ms{balancer}` ヒストグラム
  - `detection_count{type,balancer}` カウンタ
  - `correction_applied{action_type}` カウンタ
  - `conflict_resolved{strategy}` カウンタ
  - `fallback_triggered{count}` カウンタ
- **テスト**: `tests/unit/test_metrics.py` - メトリクスインクリメント・ラベル正確性

#### Step 22: 分散トレーシング対応（OpenTelemetry）
- **ファイル**: `src/narrative_balancer/arbitrator/tracing.py`
- **実装**: `trace_analyze`, `trace_integrate`, `trace_apply` スパン生成
- **属性**: `balancer.name`, `detection.count`, `correction.count`, `conflict.count`
- **テスト**: `tests/unit/test_tracing.py` - スパン階層・属性確認

#### Step 23: パフォーマンスベンチマーク
- **ファイル**: `benchmarks/benchmark_global.py`
- **測定**: 
  - 40話フル状態で p99 < 50ms（3バランサー並列込み）
  - メモリピーク < 300MB
  - 並列度スケーリング（1/2/3バランサー有効化）
- **CI**: `tests/performance/test_global_perf.py` - 閾値超過で失敗

#### Step 24: CI統合・ドキュメント・リリース
- **CI**: `.github/workflows/global_balancer.yml` (全F0-F3統合パイプライン)
  - `lint` → `typecheck` → `unit` → `integration` → `e2e` → `property` → `perf`
  - カバレッジ合算 ≥ 85%
- **ドキュメント**: `docs/global_balancer.md` - アーキテクチャ図、設定ガイド、拡張方法、トラブルシューティング
- **リリース**: `v0.1.0-global` タグ、全サブモジュール含むモノレポリリース

---

## 依存関係グラフ

```
F1/F2/F3 完成済み
    ↓
1→2→3→4
  ↓
5→6→7→8
  ↓
9→10→11→12→13→14→15
                ↓
              16→17→18→19→20
                        ↓
                      21→22→23→24
```

---

## 設定例（`config/arbitrator.yaml`）

```yaml
balancers:
  grammar:
    enabled: true
    config: "config/grammar_balancer.yaml"
    weight: 1.0
  csp:
    enabled: true
    config: "config/csp_balancer.yaml"
    weight: 0.8
  dsp:
    enabled: true
    config: "config/dsp_balancer.yaml"
    weight: 0.6

arbitration:
  priority_order: ["grammar", "csp", "dsp"]
  conflict_resolution: "HYBRID"  # PRIORITY | CONSENSUS | HYBRID
  min_consensus: 2
  hold_on_low_consensus: true

execution:
  parallel: true
  timeout_ms: 5000
  fallback_chain: ["grammar", "csp", "dsp"]  # 単独動作時の優先度

output:
  merge_strategy: "transactional"
  audit_log_enabled: true
  audit_log_path: "logs/arbitrator.jsonl"
```

---

## 実装上の重要ポイント（低性能LLM向け）

| 課題 | 対策 |
|------|------|
| **3バランサーのインターフェース差異** | `ports.py` で統一プロトコル定義、各バランサー側でアダプタ不要（既存実装が準拠） |
| **非同期並列の複雑さ** | `executor.py` に完全閉じ込め、メインフローは同期的に `asyncio.run()` 呼び出しのみ |
| **競合解決の非決定性** | 優先度順位を設定で固定、同一入力→同一出力を保証（乱数不使用） |
| **状態ミューテーションのバグ** | `applier.py` で `deepcopy` + 不変条件検証、適用前後で `PlotState` ハッシュ比較 |
| **デバッグ困難** | `audit.py` で全中間結果を JSONL 出力、`jq` でトレース可能 |

---

## 完了基準
- [ ] 全 24 ステップ マージ済み
- [ ] `pytest tests/ -k arbitrator -v` 全パス
- [ ] `pytest tests/e2e/test_global_scenarios.py -v` 全シナリオパス
- [ ] ゴールデンマスタ 15ケース 100% 一致
- [ ] `mypy --strict src/narrative_balancer/arbitrator` パス
- [ ] p99 < 50ms（3バランサー並列込み）
- [ ] 監査ログから「なぜこの補正か」がトレース可能
- [ ] 全サブモジュール含む `v0.1.0-global` リリース完了