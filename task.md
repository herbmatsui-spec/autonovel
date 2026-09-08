# タスク進行状況：第4の柱（評価・閉ループPDCAの統合）

- 計画：全72ステップ（12ステップ × 6パート）
- 検証方針：1ステップずつ丁寧に実装し、**6ステップごとに検証**して必要に応じて修正。

---

## Part 1: 8専門家オーディターの Few-shot アンカー＆Actionable Diff 統一強化 (Steps 1-12)
- [x] **Step 1**: アンカー評価用モデル `AuditAnchorExample` および `AnchorPreset` の定義 (`src/agents/specialists/anchors.py`)
- [x] **Step 2**: 読者牽引力（`reader_hook`）の 85点 / 65点 / 40点 Few-shot アンカー例文の作成 (`src/agents/specialists/anchors.py`)
- [x] **Step 3**: 論理一貫性（`consistency`）の 85点 / 65点 / 40点 Few-shot アンカー例文の作成 (`src/agents/specialists/anchors.py`)
- [x] **Step 4**: 構成力（`structure`）および起承転結の Few-shot アンカー例文の作成 (`src/agents/specialists/anchors.py`)
- [x] **Step 5**: 感情曲線（`emotion_curve`）および文体（`style`）の Few-shot アンカー例文の作成 (`src/agents/specialists/anchors.py`)
- [x] **Step 6**: 事実性（`factual`）、独創性（`creativity`）、マルチモーダル（`multimodal`）の Few-shot アンカー例文の作成 (`src/agents/specialists/anchors.py`)
- [x] **Checkpoint 1 (Step 6)**: 検証テスト実行 (`tests/unit/test_audit_anchors.py`)
- [x] **Step 7**: `SpecialistAuditor` 基底クラスへのアンカープロンプト自動注入機能の実装 (`src/agents/specialist_auditor_base.py`)
- [x] **Step 8**: `ActionableDiff` パーサーの堅牢化（曖昧なJSONやMarkdownブロックからの安定抽出） (`src/agents/specialist_auditor_base.py`)
- [x] **Step 9**: `StructureAuditor` への起承転結別 Actionable Diff 出力ロジックの実装 (`src/agents/specialists/structure_auditor.py`)
- [x] **Step 10**: `EmotionCurveAuditor` への感情落差改善 Actionable Diff 出力ロジックの実装 (`src/agents/specialists/emotion_curve_auditor.py`)
- [x] **Step 11**: `StyleAuditor` および `ConsistencyAuditor` への文体・設定矛盾 Actionable Diff 出力ロジックの実装 (`src/agents/specialists/style_auditor.py`, `src/agents/specialists/consistency_auditor.py`)
- [x] **Step 12**: Part 1 完了総合検証テスト作成 (`tests/unit/test_specialist_actionable_diffs.py`)
- [x] **Checkpoint 2 (Step 12)**: 検証テスト実行

## Part 2: 専門家スコアキャリブレーション＆正規化エンジン (Steps 13-24)
- [x] **Step 13**: キャリブレーション設定データクラス `CalibrationConfig` の定義 (`src/services/score_calibrator.py`)
- [x] **Step 14**: 専門家別・ジャンル別の事前分布統計テーブルの定義 (`src/services/score_calibrator.py`)
- [x] **Step 15**: Z-Score 変換およびシグモイドスケーリングによる 0-100点 正規化関数の実装 (`src/services/score_calibrator.py`)
- [x] **Step 16**: 自己評価信頼度（`confidence`）に基づくベイズ的スコア補正の実装 (`src/services/score_calibrator.py`)
- [x] **Step 17**: `ScoreCalibrator` クラスの本体実装 (`src/services/score_calibrator.py`)
- [x] **Step 18**: Part 2 前半単体テスト作成 (`tests/unit/test_score_calibrator.py`)
- [x] **Checkpoint 3 (Step 18)**: 検証テスト実行
- [x] **Step 19**: `AuditAggregator` への `ScoreCalibrator` 統合準備 (`src/services/audit_aggregator.py`)
- [x] **Step 20**: `BookScoreResult` へのキャリブレーション後スコアフィールド追加 (`src/services/audit_aggregator.py`)
- [x] **Step 21**: スコア乖離・異常値（Outlier）の検出とワーニング発行 (`src/services/audit_aggregator.py`)
- [x] **Step 22**: 複数サンプル採取時の分散ペナルティ計算の実装 (`src/services/audit_aggregator.py`)
- [x] **Step 23**: キャリブレーションログの監査トレース保存機能の実装 (`src/services/audit_aggregator.py`)
- [x] **Step 24**: Part 2 完了総合検証テスト作成 (`tests/unit/test_calibrated_aggregator.py`)
- [x] **Checkpoint 4 (Step 24)**: 検証テスト実行

## Part 3: 8専門家から5次元BookScoreへの数学的一元マッピング (Steps 25-36)
- [x] **Step 25**: 8専門家×5次元マッピング変換マトリクスの策定 (`src/services/book_score_mapping.py`)
- [x] **Step 26**: ジャンル別の変換マトリクス調整テーブル (`src/services/book_score_mapping.py`)
- [x] **Step 27**: 制作フェーズ別の動的重みシフターの実装 (`src/services/book_score_mapping.py`)
- [x] **Step 28**: マッピング計算エンジン `UnifiedBookScoreBridge` クラスの実装 (`src/services/book_score_mapping.py`)
- [x] **Step 29**: 欠損専門家が存在する場合の数学的比例再正規化の実装 (`src/services/book_score_mapping.py`)
- [x] **Step 30**: Part 3 前半単体テスト作成 (`tests/unit/test_book_score_mapping.py`)
- [x] **Checkpoint 5 (Step 30)**: 検証テスト実行
- [x] **Step 31**: `BookScoreCalculator` のリファクタリング（`UnifiedBookScoreBridge` 委譲） (`src/services/book_score_service.py`)
- [x] **Step 32**: 5次元スコアの内訳寄与度の算出メソッド実装 (`src/services/book_score_service.py`)
- [x] **Step 33**: `BookScoreModel`（DBモデル）への 8専門家内訳 JSON フィールド保存対応 (`src/services/book_score_service.py`)
- [x] **Step 34**: 8専門家スコアと5次元BookScoreの双方向インデックス取得API (`src/services/book_score_service.py`)
- [x] **Step 35**: 統一成熟度評価レポート生成メソッドの実装 (`src/services/book_score_service.py`)
- [x] **Step 36**: Part 3 完了総合検証テスト作成 (`tests/unit/test_unified_book_score.py`)
- [x] **Checkpoint 6 (Step 36)**: 検証テスト実行

## Part 4: クローズドループPDCAエンジン（特化再生成ディレクティブ生成） (Steps 37-48)
- [x] **Step 37**: 執筆必須制約モデル `WritingDirective` および `PDCACycleResult` の定義 (`src/services/pdca_directive.py`)
- [x] **Step 38**: 最低スコア次元特定アルゴリズムの実装 (`src/services/pdca_directive.py`)
- [x] **Step 39**: Actionable Diff から執筆プロンプト制約への自動変換エンジンの実装 (`src/services/pdca_directive.py`)
- [x] **Step 40**: 次元別の特化プロンプトテンプレート定義 (`src/services/pdca_directive.py`)
- [x] **Step 41**: ディレクティブ優先順位ソート（重大度・スコア乖離度順） (`src/services/pdca_directive.py`)
- [x] **Step 42**: Part 4 前半単体テスト作成 (`tests/unit/test_pdca_directive.py`)
- [x] **Checkpoint 7 (Step 42)**: 検証テスト実行
- [x] **Step 43**: クローズドループ再生成マネージャ `ClosedLoopPDCARunner` クラスの設計 (`src/services/pdca_cycle.py`)
- [x] **Step 44**: 再執筆実行（`WriterAgent` へのディレクティブ注入）と再監査のオーケストレーション (`src/services/pdca_cycle.py`)
- [x] **Step 45**: 再生成前後のスコア差分（Before vs After）および改善率算出機能 (`src/services/pdca_cycle.py`)
- [x] **Step 46**: 早期終了判定（目標スコア到達、またはスコア改善率停滞・収束検知）の実装 (`src/services/pdca_cycle.py`)
- [x] **Step 47**: 再執筆履歴スナップショット（各サイクルのドラフト・スコア・適用ディレクティブ）の記録 (`src/services/pdca_cycle.py`)
- [x] **Step 48**: Part 4 完了総合検証テスト作成 (`tests/unit/test_closed_loop_pdca.py`)
- [x] **Checkpoint 8 (Step 48)**: 検証テスト実行

## Part 5: DAGタスクスケジューラーの動的リプランニング（局所リトライ＆安全キャンセル） (Steps 49-60)
- [x] **Step 49**: DAG動的リプランニング状態モデル `DAGReplanningState` の定義 (`src/backend/tasks/dag_replanning.py`)
- [x] **Step 50**: タスク依存グラフにおける下流タスク（Downstream Tasks）特定アルゴリズムの実装 (`src/backend/tasks/dag_replanning.py`)
- [x] **Step 51**: 局所リトライ（再執筆対象ノードのみの再スケジュール）ロジックの実装 (`src/backend/tasks/dag_replanning.py`)
- [x] **Step 52**: 実行中後続タスクの安全なキャンセル＆ロールバック機構の実装 (`src/backend/tasks/dag_replanning.py`)
- [x] **Step 53**: `DAGTaskScheduler` と `DAGReplanner` のブリッジ設計 (`src/backend/tasks/dag_replanning.py`)
- [x] **Step 54**: Part 5 前半単体テスト作成 (`tests/unit/test_dag_replanning.py`)
- [x] **Checkpoint 9 (Step 54)**: 検証テスト実行
- [x] **Step 55**: `DAGScheduler` への `DynamicDAGReplanner` フック統合 (`src/backend/tasks/dag_scheduler.py`)
- [x] **Step 56**: 局所リトライ成功時の下流ノード自動再アクティベーション処理 (`src/backend/tasks/dag_scheduler.py`)
- [x] **Step 57**: リトライ上限到達時の安全な全体フェイルセーフ処理 (`src/backend/tasks/dag_scheduler.py`)
- [x] **Step 58**: リプランニングログおよびメトリクス集計（リトライ回数、キャンセルタスク数） (`src/backend/tasks/dag_scheduler.py`)
- [x] **Step 59**: EventBus への `dag.replanned` イベント発行機能 (`src/backend/tasks/dag_scheduler.py`)
- [x] **Step 60**: Part 5 完了総合検証テスト作成 (`tests/unit/test_dag_scheduler_replanning.py`)
- [x] **Checkpoint 10 (Step 60)**: 検証テスト実行

## Part 6: 商業水準ベンチマーク・E2E結合テスト・Final Gate (Steps 61-72)
- [x] **Step 61**: 商業品質基準モデル `CommercialQualityMetrics` の定義 (`src/services/commercial_benchmarks.py`)
- [x] **Step 62**: 商業出版水準（85+）・Web連載人気水準（75+）判定器の実装 (`src/services/commercial_benchmarks.py`)
- [x] **Step 63**: 読者離脱リスク指標の定量化ロジック (`src/services/commercial_benchmarks.py`)
- [x] **Step 64**: 定量ベンチマーク判定・改善率（>=15%）検証の実装 (`src/services/commercial_benchmarks.py`)
- [x] **Step 65**: 7大ヘルスチェック実行機能の実装 (`src/services/commercial_benchmarks.py`)
- [x] **Step 66**: 商業品質・ヘルスチェック単体テスト作成 (`tests/unit/test_commercial_benchmarks.py`)
- [x] **Checkpoint 11 (Step 66)**: 検証テスト実行
- [x] **Step 67**: E2E結合テスト 2: 監査不合格時のDAG動的リプランニング＆局所リトライ E2E (`tests/integration/test_dag_replanning_e2e.py`)
- [x] **Step 68**: ヘルスチェックスクリプトの作成と実行 (`scripts/health_check_pillar4.py`)
- [x] **Step 69**: 第4の柱 アーキテクチャガイドの整備 (`docs/ARCHITECTURE_PILLAR4.md`)
- [x] **Step 70**: 第4の柱 全体包括的回帰テストの作成・実行 (`tests/integration/test_pillar4_full_regression.py`)
- [x] **Step 71**: コードベース全体のクリーンアップ、構文コンパイル、不要ログの整理
- [x] **Step 72**: Final Gate (Checkpoint 12) - 全テストスイート一括実行 (100% ALL GREEN)
