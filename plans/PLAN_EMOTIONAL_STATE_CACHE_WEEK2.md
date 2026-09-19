# PLAN: 感情状態キャッシュ Week 2 - ルールエンジン＋プロット連動ベースライン生成
**目標**: プロットイベント定義 → 感情変化ルール適用 → ベースラインベクトル自動生成 → Vector/Graph/Log へ永続化
**前提**: Week 1 の VectorStore/GraphStore/LogStore インターフェースを前提とする。LLM呼び出しなし。

---

## Step 1-24 実装タスク

### Phase 1: プロットイベント・ルールスキーマ定義 (Steps 1-6)

**Step 1: プロットイベント型定義**
- ファイル: `src/rules/plot_events.py` (新規)
- Enum: `PlotEventType` (BETRAYAL, RESCUE, CONFESSION, COMBAT_VICTORY, LOSS_OF_LOVED_ONE, SECRET_SHARED, FORCED_COOPERATION, REJECTION, CUSTOM)
- Dataclass: `PlotEvent` (event_id, episode, scene, event_type, roles: Dict[Role, str], metadata: Dict)
- Enum: `Role` (VICTIM, PERPETRATOR, RESCUER, WITNESS, SHARER, RECEIVER, PARTICIPANT, CONFESSOR, LISTENER)
- テスト: `tests/unit/rules/test_plot_events.py::test_plot_event_creation`

**Step 2: 感情変化ルール定義**
- ファイル: `src/rules/emotional_rules.py` (新規)
- Dataclass: `EmotionalRule` (event_type, source_role, target_role, emotion_deltas: Dict[EmotionType, float], condition: Callable[[PlotContext], bool], decay_per_episode: float)
- Dataclass: `PlotContext` (episode, event, roles, relationship_level, previous_tension, custom_data)
- デフォルト条件: `lambda ctx: True`
- テスト: `tests/unit/rules/test_emotional_rules.py::test_rule_creation`

**Step 3: ルールセット YAML 定義ファイル**
- ファイル: `config/emotional_rules.yaml` (新規)
- 構造:
  ```yaml
  rules:
    - event_type: "betrayal"
      source_role: "victim"
      target_role: "perpetrator"
      emotion_deltas:
        affection: -0.6
        tension: +0.8
        fear: +0.5
        trust: -0.7
      decay_per_episode: 0.1
    - event_type: "rescue"
      source_role: "victim"
      target_role: "rescuer"
      emotion_deltas:
        affection: +0.4
        trust: +0.5
        tension: -0.3
      decay_per_episode: 0.05
  ```
- テスト: `tests/unit/config/test_emotional_rules_yaml.py::test_yaml_loads_all_rules`

**Step 4: ルールローダー実装**
- ファイル: `src/rules/rule_loader.py` (新規)
- クラス: `RuleLoader`
- メソッド: `load_rules(path: str) -> List[EmotionalRule]`
- 条件関数: 文字列式を `eval` せず、事前定義関数マップから参照 (`condition_registry`)
- レジストリ: `src/rules/conditions.py` に定義済み関数を登録
- テスト: `tests/unit/rules/test_rule_loader.py::test_load_rules_with_conditions`

**Step 5: 条件関数レジストリ**
- ファイル: `src/rules/conditions.py` (新規)
- 関数群:
  - `relationship_above(ctx, threshold) -> bool`
  - `tension_above(ctx, threshold) -> bool`
  - `previous_event_was(ctx, event_type) -> bool`
  - `custom_flag(ctx, flag_name) -> bool`
- デコレータ: `@condition_registry.register("name")` で自動登録
- テスト: `tests/unit/rules/test_conditions.py::test_relationship_above`

**Step 6: プロットイベント入力ファイル形式**
- ファイル: `config/plot_events.yaml` (新規)
- 構造: エピソードごとのイベントリスト
- 例:
  ```yaml
  episode_14:
    - event_id: "ep14_betrayal"
      event_type: "betrayal"
      scene: 3
      roles:
        victim: "A"
        perpetrator: "B"
      metadata: {witness: "C"}
  ```
- テスト: `tests/unit/config/test_plot_events_yaml.py::test_parse_episode_events`

---

### Phase 2: ルールエンジン実装 (Steps 7-14)

**Step 7: 感情状態マシン (ペアごと状態管理)**
- ファイル: `src/rules/state_machine.py` (新規)
- クラス: `EmotionalStateMachine`
- 内部状態: `Dict[Tuple[str, str, EmotionType], float]` (source, target, emotion) → value
- メソッド:
  - `apply_delta(source, target, emotion, delta) -> float` (クランプ付き加算、新値返却)
  - `get_state(source, target) -> Dict[EmotionType, float]`
  - `decay_all(factor: float)` (全状態に減衰適用)
  - `snapshot() -> Dict` (シリアライズ用)
- テスト: `tests/unit/rules/test_state_machine.py::test_apply_delta_and_clamp`

**Step 8: ルールエンジンコア**
- ファイル: `src/rules/engine.py` (新規)
- クラス: `RuleEngine`
- `__init__(rules: List[EmotionalRule], state_machine: EmotionalStateMachine)`
- メソッド: `process_event(event: PlotEvent, context: PlotContext) -> List[EmotionalSignal]`
- ロジック:
  1. マッチするルール抽出 (event_type 一致)
  2. 条件関数評価
  3. roles から source/target 解決
  4. state_machine.apply_delta 実行
  5. EmotionalSignal 生成 (evidence_span に event_id 記録)
- テスト: `tests/unit/rules/test_engine.py::test_process_betrayal_event`

**Step 9: エピソード一括処理機能**
- ファイル: `src/rules/engine.py` (追加)
- メソッド: `process_episode(episode: int, events: List[PlotEvent], initial_context: PlotContext) -> EmotionalVector`
- フロー:
  1. エピソード開始時: 前回スナップショットから state_machine 復元
  2. 各イベント順に `process_event`
  3. エピソード終了時: `state_machine.snapshot()` 保存
  4. 最終状態を `EmotionalVector` に変換して返却
- テスト: `tests/unit/rules/test_engine.py::test_process_full_episode`

**Step 10: 減衰処理の自動適用**
- ファイル: `src/rules/engine.py` (追加)
- メソッド: `apply_inter_episode_decay(episodes_passed: int)`
- 各ルールの `decay_per_episode` を使用: `value *= (1 - decay) ** episodes_passed`
- エピソード境界で自動呼び出し
- テスト: `tests/unit/rules/test_engine.py::test_decay_across_episodes`

**Step 11: GraphStore インターフェース実装 (Kuzu/FalkorDB)**
- ファイル: `src/stores/graph_store.py` (新規)
- クラス: `GraphStore` (ABC), `KuzuGraphStore` (実装)
- スキーマ: ノード `Character(name)`, エッジ `FEELS_TOWARD{affection, tension, fear, trust, intimacy, cause, episode, timestamp}`
- メソッド:
  - `upsert_edge(source, target, props: Dict)`
  - `get_latest_edge(source, target) -> Dict`
  - `query_causal_path(source, target, max_hops=3) -> List[Dict]`
- テスト: `tests/unit/stores/test_graph_store.py::test_upsert_and_query` (モックDB使用)

**Step 12: EventLog ストア実装 (JSONL append-only)**
- ファイル: `src/stores/event_log.py` (新規)
- クラス: `EventLogStore`
- ファイル: `data/emotional_events.jsonl` (1行1イベント)
- メソッド:
  - `append(signal: EmotionalSignal)`
  - `query(pair: Tuple[str,str], from_ep: int, to_ep: int) -> List[EmotionalSignal]`
  - `replay_to_episode(episode: int) -> EmotionalStateMachine` (全再生で状態復元)
- テスト: `tests/unit/stores/test_event_log.py::test_append_and_query`

**Step 13: エンジン統合・永続化フック**
- ファイル: `src/rules/engine.py` (追加)
- メソッド: `persist_results(vector_store, graph_store, log_store, episode: int)`
- 呼び出しタイミング: `process_episode` 完了後
- 書き込み:
  - Vector: `vector_store.upsert(f"rule_engine:ep{episode}", vector)`
  - Graph: 各 signal から `graph_store.upsert_edge()`
  - Log: 各 signal を `log_store.append()`
- テスト: `tests/integration/rules/test_engine_persistence.py::test_persist_to_all_stores`

**Step 14: ルールエンジン統合テスト**
- ファイル: `tests/integration/rules/test_rule_engine_e2e.py` (新規)
- 入力: `config/plot_events.yaml` (ep14-16 分のサンプル)
- 実行: `engine.process_episode` × 3話
- 検証:
  - VectorStore に `rule_engine:ep14`, `ep15`, `ep16` 存在
  - Graph にエッジ 3話分蓄積
  - Log に全シグナル記録
  - 既知ペアの値が期待レンジ内

---

### Phase 3: パイプライン統合・ベースライン生成 (Steps 15-18)

**Step 15: パイプラインへのルールエンジンステージ追加**
- ファイル: `src/pipeline/compression_pipeline.py` (既存編集)
- インポート: `RuleEngine`, `RuleLoader`, `PlotEvent` parser
- `__init__` に `rule_engine` パラメータ追加
- `run()` 内で: エピソード開始前に `rule_engine.process_episode()` 実行
- 設定フラグ: `pipeline.yaml` に `rule_engine: {enabled: true}`
- テスト: `tests/unit/pipeline/test_rule_engine_stage.py::test_rule_engine_stage_runs`

**Step 16: ベースラインベクトルとパイプライン抽出ベクトルの併存**
- ファイル: `src/pipeline/compression_pipeline.py` (追加)
- ネームスペース分離:
  - `pipeline` (Week 1 の自動抽出)
  - `rule_engine` (Week 2 のベースライン)
  - `annotation` (Week 3 の人間上書き)
- 両方とも保存、融合は読み取り側 (Week 4) で実施
- テスト: `tests/integration/pipeline/test_dual_vector_sources.py::test_both_vectors_stored`

**Step 17: プロットイベントファイル監視・自動再計算 (オプション)**
- ファイル: `src/rules/watcher.py` (新規、簡易版)
- 関数: `recompute_from_episode(start_ep: int)` 
- 用途: プロット修正時の手動再計算コマンド
- CLI: `python -m src.rules.watcher recompute --from 14`
- テスト: `tests/unit/rules/test_watcher.py::test_recompute_from_episode`

**Step 18: ベースライン生成精度テスト**
- ファイル: `tests/regression/test_rule_engine_regression.py` (新規)
- フィクスチャ: 既知プロットイベント列 → 期待感情ベクトル
- ケース:
  - `test_betrayal_then_rescue`: 裏切り→救出で恐怖減衰・信頼回復
  - `test_forced_coop_high_tension`: 高緊張下の強制協力で緊張微増・理解増
  - `test_decay_over_5_episodes`: 5話放置で値が半減以下に

---

### Phase 4: 設定・ドキュメント・リグレッション (Steps 19-24)

**Step 19: ルールセット拡張ガイド**
- ファイル: `docs/emotional_rules_authoring.md` (新規)
- 内容: 新規イベントタイプ追加手順、条件関数追加手順、デバッグ用ログ出力方法

**Step 20: 開発者向けデバッグCLI**
- ファイル: `src/rules/debug_cli.py` (新規)
- コマンド:
  - `show-state --episode 15 --pair A B`
  - `show-graph-path --source A --target B`
  - `show-log --pair A B --from 10 --to 15`
- テスト: `tests/unit/rules/test_debug_cli.py::test_show_state`

**Step 21: 既存テストへのリグレッション追加**
- ファイル: `tests/regression/test_week2_regression.py` (新規)
- ケース:
  - `test_rule_engine_does_not_break_pipeline`: パイプライン全体実行成功
  - `test_vector_namespaces_isolated`: pipeline/rule_engine/annotation が混ざらない
  - `test_graph_query_returns_causal_path`: 因果パス取得が動作

**Step 22: CI/CD 追加**
- ファイル: `.github/workflows/rule_engine.yml` (新規)
- ジョブ: `unit-rules`, `integration-rules`, `regression-week2`
- 依存: `needs: [emotional_residue_week1]` (Week1 成功後に実行)

**Step 23: パフォーマンステスト**
- ファイル: `tests/performance/test_rule_engine_perf.py` (新規)
- 測定: 100イベント処理時間 < 100ms, メモリ増加 < 50MB
- ベンチマーク: `pytest --benchmark-only`

**Step 24: Week 2 完了チェックリスト・ドキュメント**
- ファイル: `docs/emotional_state_cache_week2.md` (新規)
- 内容:
  - ルール定義・追加方法
  - プロットイベントファイル形式
  - 再計算コマンド使い方
  - Graph/Log 確認方法
  - Week 1 との併用時の挙動

---

## 完了基準 (Definition of Done)

- [ ] 全 Step 1-24 テストパス (CI グリーン)
- [ ] `config/plot_events.yaml` サンプルで 3話分ベースライン生成確認
- [ ] Vector (rule_engine), Graph, Log の 3ストアに正しく書き込まれる
- [ ] 減衰処理が話境界で正しく動作
- [ ] リグレッションテスト 3ケース + Week1 リグレッション全パス
- [ ] デバッグCLI で状態・グラフ・ログが確認できる
- [ ] Week 1 機能に影響なし (併存確認済み)