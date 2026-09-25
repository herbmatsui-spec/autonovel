# PLAN: 感情状態キャッシュ Week 4 - 融合レイヤー＋矛盾検出・アラート
**目標**: 3ソース (pipeline/rule_engine/annotation) の感情ベクトルを融合 → 単一ビュー提供 → 矛盾検出・編集者アラート → 信頼度ベース仲裁
**前提**: Week 1-3 の 3ネームスペース (pipeline, rule_engine, annotation) が VectorStore に独立保存済み

---

## Step 1-24 実装タスク

### Phase 1: 融合エンジンコア (Steps 1-8)

**Step 1: 融合用データ構造定義**
- ファイル: `src/fusion/models.py` (新規)
- Dataclass: `SourceVector` (namespace: str, vector: EmotionalVector, confidence: float, timestamp: datetime)
- Dataclass: `FusedVector` (values: Dict[Tuple[str,str,EmotionType], FusedValue], conflicts: List[Conflict], metadata: Dict)
- Dataclass: `FusedValue` (value: float, primary_source: str, contributing_sources: List[str], confidence: float)
- Dataclass: `Conflict` (pair: Tuple[str,str], emotion: EmotionType, sources: List[Tuple[str, float, float]]) # (source, value, confidence)
- テスト: `tests/unit/fusion/test_models.py::test_fused_value_creation`

**Step 2: 信頼度デフォルト値設定**
- ファイル: `config/fusion.yaml` (新規)
- 構造:
  ```yaml
  source_confidence:
    annotation: 1.0
    rule_engine: 0.8
    pipeline: 0.5
  conflict_threshold: 0.3  # 絶対値差がこれ以上で矛盾とみなす
  significance_threshold: 0.3  # 両方がこの絶対値以上で矛盾判定
  blend_weights:
    annotation: 0.7
    rule_engine: 0.2
    pipeline: 0.1
  ```
- テスト: `tests/unit/config/test_fusion_config.py::test_load_confidence_defaults`

**Step 3: 設定ローダー**
- ファイル: `src/fusion/config.py` (新規)
- クラス: `FusionConfig` (Pydantic BaseModel 推奨)
- 関数: `load_fusion_config() -> FusionConfig` (シングルトン)
- 環境変数オーバーライド対応: `FUSION_CONF_ANNOTATION=0.9` 等
- テスト: `tests/unit/fusion/test_config.py::test_env_override`

**Step 4: ベクトル収集器**
- ファイル: `src/fusion/collector.py` (新規)
- クラス: `VectorCollector`
- `__init__(vector_store: VectorStore, config: FusionConfig)`
- メソッド: `collect_all(pair: Tuple[str,str]) -> List[SourceVector]`
- ロジック: 3ネームスペース全てから `get_latest` 試行、存在するもののみ収集
- タイムスタンプ付与 (VectorStore が持つ場合) または現在時刻
- テスト: `tests/unit/fusion/test_collector.py::test_collect_from_multiple_namespaces`

**Step 5: 矛盾検出器**
- ファイル: `src/fusion/conflict_detector.py` (新規)
- クラス: `ConflictDetector`
- `__init__(config: FusionConfig)`
- メソッド: `detect(source_vectors: List[SourceVector]) -> List[Conflict]`
- アルゴリズム:
  1. 同一 (pair, emotion) でグループ化
  2. 信頼度降順ソート
  3. 最上位 vs 2位: 符号異なる AND 両方 `abs(value) >= significance_threshold` AND `abs(v1-v2) >= conflict_threshold`
  4. 矛盾レコード生成
- テスト: `tests/unit/fusion/test_conflict_detector.py::test_detect_sign_conflict`

**Step 6: 仲裁・融合ロジック**
- ファイル: `src/fusion/arbitrator.py` (新規)
- クラス: `Arbitrator`
- `__init__(config: FusionConfig, conflict_detector: ConflictDetector)`
- メソッド: `fuse(source_vectors: List[SourceVector]) -> FusedVector`
- アルゴリズム:
  1. `conflict_detector.detect()` で矛盾リスト取得
  2. 矛盾なし項目: 最高信頼度ソースの値を採用 (`primary_source` 記録)
  3. 矛盾あり項目: 
     - 設定 `blend_weights` で加重平均計算 (信頼度×重みで正規化)
     - または `highest_confidence_wins` モード (設定で切替)
     - `primary_source` = 最高信頼度ソース、`contributing_sources` = 全寄与ソース
  4. 信頼度計算: `primary_confidence * (1 - conflict_penalty)` (矛盾時ペナルティ)
- テスト: `tests/unit/fusion/test_arbitrator.py::test_fuse_no_conflict`, `test_fuse_with_conflict_blend`

**Step 7: 全ペア一括融合**
- ファイル: `src/fusion/engine.py` (新規)
- クラス: `FusionEngine`
- `__init__(vector_store, config, arbitrator, collector)`
- メソッド: `fuse_all(episode: int) -> FusedVector`
- ロジック:
  1. 全ネームスペースから全キー取得 (`vector_store.get_all_namespace_keys()`)
  2. ペアごとに `collector.collect_all()` → `arbitrator.fuse()`
  3. 結果を `FusedVector` に集約
- テスト: `tests/unit/fusion/test_engine.py::test_fuse_all_pairs`

**Step 8: 融合結果永続化 (キャッシュ)**
- ファイル: `src/fusion/engine.py` (追加)
- メソッド: `persist_fused(fused: FusedVector, episode: int)`
- 書き込み先: `VectorStore` namespace=`fused`, key=`ep{episode}`
- 併せて: `ConflictStore` (新規、簡易JSONまたはRedis Hash) に矛盾記録
- TTL: 次回融合まで (上書き)
- テスト: `tests/integration/fusion/test_persist_fused.py::test_fused_vector_stored`

---

### Phase 2: プロンプト統合・アラートシステム (Steps 9-14)

**Step 9: 融合ベクトル用プロンプトテンプレート**
- ファイル: `templates/fused_emotional_context.j2` (新規)
- 入力: `FusedVector`
- 出力構造:
  ```
  [直前話からの引き継ぎ感情（融合済み）]
  ## 高信頼度（作者指定・プロット整合）
  A→B: 恐怖(0.8) - 第14話裏切り事件が原因 [annotation]
  B→A: 罪悪感(0.6) [annotation]
  
  ## 中信頼度（プロットルール推定）
  A→C: 緊張(0.4) [rule_engine]
  
  ## 低信頼度（自動抽出・参考）
  C→A: 好意(0.2) [pipeline]
  
  ## ⚠ 矛盾検出（要確認）
  A→D: annotation=信頼(0.7) vs pipeline=不信(-0.5)
  ```
- 矛盾セクションは `conflicts` 存在時のみ表示
- テスト: `tests/unit/templates/test_fused_context.py::test_render_with_conflicts`

**Step 10: プロンプトビルダー統合 (融合版)**
- ファイル: `src/pipeline/prompt_builder.py` (Week 1,3 既存編集)
- 関数: `build_fused_emotional_context_prompt(episode: int, fusion_engine: FusionEngine) -> str`
- フロー: `fusion_engine.fuse_all(episode-1)` → テンプレート描画
- 既存 `build_emotional_context_prompt` を非推奨化・内部で融合版呼び出しに変更
- テスト: `tests/unit/pipeline/test_prompt_builder_fused.py::test_fused_prompt_includes_conflicts`

**Step 11: 矛盾アラート通知システム**
- ファイル: `src/fusion/alerts.py` (新規)
- クラス: `ConflictAlerter`
- メソッド: `alert(conflicts: List[Conflict], episode: int, context: Dict)`
- チャネル (設定可):
  - ログ出力 (WARNING レベル, 構造化JSON)
  - ファイル追記: `logs/conflicts_ep{episode}.jsonl`
  - Webhook: `POST /webhooks/conflict-alert` (Slack/Discord/独自)
  - メール: 既存メール送信機能流用
- 通知内容: 矛盾ペア、感情、各ソース値・信頼度、推奨アクション
- テスト: `tests/unit/fusion/test_alerts.py::test_alert_logs_warning`

**Step 12: 編集者向け矛盾レビュー API**
- ファイル: `src/api/conflicts.py` (新規)
- エンドポイント:
  - `GET /api/conflicts?episode=15` → 該当話の矛盾一覧
  - `GET /api/conflicts/{conflict_id}` → 詳細 (履歴含む)
  - `POST /api/conflicts/{conflict_id}/resolve` `{resolution: "annotation" | "rule_engine" | "pipeline" | "manual", manual_value: float?}` → 手動解決記録
- 解決記録: `ConflictResolutionStore` (JSONL) に保存、次回融合で反映
- テスト: `tests/integration/api/test_conflict_resolution.py::test_resolve_conflict_manual`

**Step 13: 解決済み矛盾の融合反映**
- ファイル: `src/fusion/arbitrator.py` (修正)
- 修正: `fuse()` 内で `ConflictResolutionStore` 照会
- 解決済み矛盾: 指定通りの値・ソースを強制採用 (信頼度 1.0 扱い)
- テスト: `tests/unit/fusion/test_arbitrator_resolved.py::test_resolved_conflict_overrides`

**Step 14: 統合プロンプト生成フロー完全置換**
- ファイル: `src/agents/writer_agent.py` またはプロンプト生成箇所 (既存編集)
- 変更: 従来の単一ソース取得 → `build_fused_emotional_context_prompt()` 一本化
- 互換性: 設定 `fusion.enabled=true` で切替、false なら従来ロジック (移行期間用)
- テスト: `tests/integration/agent/test_writer_fused_prompt.py::test_writer_uses_fused_prompt`

---

### Phase 3: 分析・可視化・デバッグ支援 (Steps 15-18)

**Step 15: 融合プロセス可視化 CLI**
- ファイル: `src/fusion/debug_cli.py` (新規)
- コマンド:
  - `fusion show --episode 15 --pair A B` → 3ソース値・融合結果・矛盾表示
  - `fusion conflicts --episode 15` → 矛盾一覧
  - `fusion explain --episode 15 --pair A B --emotion fear` → なぜこの値か説明 (信頼度・重み・矛盾有無)
- 出力: リッチテキスト (rich ライブラリ) または JSON
- テスト: `tests/unit/fusion/test_debug_cli.py::test_show_command`

**Step 16: 感情推移ダッシュボード用データ API**
- ファイル: `src/api/dashboard.py` (新規)
- エンドポイント:
  - `GET /api/dashboard/timeline?pair=A,B&from=10&to=20` → 時系列データ (各ソース別系列 + 融合系列)
  - `GET /api/dashboard/conflicts?from=1&to=50` → 期間内矛盾サマリー (件数・傾向)
  - `GET /api/dashboard/source_contribution?episode=15` → ソース別採用率統計
- レスポンス: Chart.js 直接食わせ可能な形式
- テスト: `tests/integration/api/test_dashboard.py::test_timeline_endpoint`

**Step 17: ソース別貢献度分析ログ**
- ファイル: `src/fusion/analytics.py` (新規)
- 関数: `analyze_source_contribution(fused_history: List[FusedVector]) -> Dict`
- 指標:
  - ソース別採用率 (全感情値中、primary_source となった割合)
  - 矛盾発生率・解決率
  - 信頼度分布
- 実行: 夜間バッチまたは手動 CLI `fusion analytics --last 50`
- 出力: `logs/fusion_analytics_YYYYMMDD.json`
- テスト: `tests/unit/fusion/test_analytics.py::test_contribution_analysis`

**Step 18: 異常検知・自動アラート**
- ファイル: `src/fusion/anomaly.py` (新規)
- ルール:
  - 矛盾数が前話比 2倍超 → アラート
  - 特定ソース (annotation) が 3話連続未更新 → アラート (作者未記入)
  - 融合信頼度平均が閾値 (0.6) 未満 → アラート
- 実行: `FusionEngine.fuse_all()` 完了時フック
- テスト: `tests/unit/fusion/test_anomaly.py::test_conflict_spike_alert`

---

### Phase 4: 設定・テスト・ドキュメント (Steps 19-24)

**Step 19: 融合設定の完全外部化**
- ファイル: `config/fusion.yaml` (Step 2 拡張)
- 追加項目:
  - `mode: "highest_confidence" | "weighted_blend"`
  - `conflict_penalty: 0.2`
  - `alert_channels: ["log", "webhook"]`
  - `webhook_url: "..."`
  - `anomaly_thresholds: {conflict_spike: 2.0, annotation_stale_episodes: 3, min_avg_confidence: 0.6}`

**Step 20: 包括的リグレッションテスト**
- ファイル: `tests/regression/test_week4_regression.py` (新規)
- ケース:
  - `test_annotation_wins_no_conflict`: アノテーション単独なら確実採用
  - `test_rule_engine_fallback`: アノテーションない時ルールエンジン採用
  - `test_pipeline_last_resort`: 両方ない時パイプライン採用
  - `test_conflict_detected_sign_flip`: 符号反転で矛盾検出
  - `test_conflict_blend_mode`: 加重平均で中間値
  - `test_manual_resolution_persists`: 手動解決が次回融合に反映
  - `test_fused_prompt_format`: プロンプトに全セクション含む
  - `test_alert_on_conflict`: 矛盾時にアラート発火

**Step 21: 既存テストの融合版対応更新**
- ファイル: `tests/integration/pipeline/test_full_pipeline.py` (既存編集)
- 修正: プロンプト生成期待値を融合版テンプレート対応に更新
- 確認: Week 1-3 の統合テストが融合版でもパスすること

**Step 22: パフォーマンステスト・ベンチマーク**
- ファイル: `tests/performance/test_fusion_perf.py` (新規)
- 測定:
  - 100ペア融合 < 50ms
  - 矛盾検出 1000ペア < 100ms
  - メモリ: 融合エンジンインスタンス < 10MB
- ベンチマーク: `pytest --benchmark-only tests/performance/test_fusion_perf.py`

**Step 23: CI/CD パイプライン追加**
- ファイル: `.github/workflows/fusion.yml` (新規)
- ジョブ: `unit-fusion`, `integration-fusion`, `regression-week4`, `perf-fusion`
- 依存: `needs: [week3]`
- アーティファクト: ベンチマーク結果, カバレッジレポート

**Step 24: Week 4 完了ドキュメント・運用ガイド**
- ファイル: `docs/emotional_state_cache_week4.md` (新規)
- 内容:
  - 融合ロジック詳細 (信頼度・重み・矛盾判定式)
  - 矛盾アラート運用フロー (検知→通知→レビュー→解決)
  - 手動解決 API 使い方
  - ダッシュボードデータ活用法
  - 設定チューニング指針 (信頼度重み調整等)
  - トラブルシューティング

---

## 完了基準 (Definition of Done)

- [ ] 全 Step 1-24 テストパス (CI グリーン)
- [ ] 3ソース融合 → 単一 `FusedVector` 生成確認
- [ ] 矛盾検出: 符号反転・有意差で正しく検知、アラート発火
- [ ] 手動解決 API で矛盾解消 → 次回融合に反映確認
- [ ] 次話プロンプトが融合版テンプレートで生成 (ソース別表示・矛盾セクション含む)
- [ ] ダッシュボード API で時系列・貢献度取得可能
- [ ] Week 1-3 全リグレッションテストパス (融合版プロンプトでも従来機能動作)
- [ ] デバッグ CLI で融合プロセス完全トレース可能