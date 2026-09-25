# PLAN_B1: SubversionEngine ネイティブ統合（正統進化アプローチ）

**目標**: 既存エンジン構造（`BaseEngine`/`extra_engines`/FlatModelMixin）に `SubversionEngine` を第4のエンジンとしてネイティブ統合し、Arc・Beat・Scene全層で「3話ごとの裏切り」を決定論的にスケジュール・適用・検証する。

**前提**: `src/models/plot.py` の `PlotEpisode` が `EnigmaMixin`/`ComfortMixin` を継承している構造を踏襲し、`SubversionMixin` を追加する。

---

## Step 1: `src/models/subversion.py` 新規作成（モデル定義）

**作業内容**
- `SubversionPattern` / `SubversionEngine` クラスを定義
- `BaseEngine` 継承、`get_routing_keys()` 実装
- `plan_schedule()` / `apply_to_arc()` / `apply_to_beat()` / `validate_coherence()` 実装
- 決定論的パターン選択（MD5シード）実装

**受け入れ基準**
- `python -c "from src.models.subversion import SubversionEngine; e=SubversionEngine(); e.plan_schedule(40); print(len(e.schedule))"` で `13` が出力される
- 同一条件で2回実行しても同一スケジュールが生成される

**テスト作成**: `tests/test_subversion_engine.py::test_plan_schedule_deterministic`

---

## Step 2: `SubversionPattern` 単体テスト

**作業内容**
- `tests/test_subversion_engine.py` 作成
- パターンA/B/C の `description`/`cost`/`payoff_hint` が空でないことを確認
- `trigger_ep` が正の整数であることを確認

**受け入れ基準**: `pytest tests/test_subversion_engine.py::test_pattern_fields -v` が通る

---

## Step 3: `SubversionEngine.validate_coherence()` テスト

**作業内容**
- 重複話数・間隔不足・終盤回収ヒント不足のケースを作り、エラー検出を確認
- 正常ケースで空リストが返ることを確認

**受け入れ基準**: `pytest tests/test_subversion_engine.py::test_validate_coherence -v` が通る

---

## Step 4: `src/models/plot.py` へ `SubversionMixin` 追加

**作業内容**
- `SubversionMixin` クラス定義（`subversion: SubversionEngine = Field(default_factory=SubversionEngine)`）
- `PlotEpisode` 継承リストに `SubversionMixin` を追加
- 循環インポート回避のため `TYPE_CHECKING` ブロックでインポート

**受け入れ基準**
- `python -c "from src.models.plot import PlotEpisode; print(hasattr(PlotEpisode, 'subversion'))"` で `True`
- 既存テスト `pytest tests/test_plot_models.py -v` が全通過（リグレッション確認）

---

## Step 5: `PlotEpisode` シリアライズ/デシリアライズ テスト

**作業内容**
- `PlotEpisode` に `subversion` フィールドを含む JSON ダンプ/ロードが正常に行えることを確認
- `extra_engines` 経由で正しく保存・復元されることを確認

**テスト作成**: `tests/test_plot_models.py::test_subversion_mixin_serialization`

---

## Step 6: `src/agents/planning.py` にインポート・初期化ロジック追加

**作業内容**
- `from src.models.subversion import SubversionEngine` 追加
- `generate_arcs()` 内で `SubversionEngine` インスタンス生成・設定適用
- 設定値は `ctx.artifacts.get("subversion", {})` から取得（デフォルト値あり）

**受け入れ基準**: インポートエラーなし。既存 `generate_arcs` テストが通る

---

## Step 7: `generate_arcs()` でスケジュール生成・Arc へ適用

**作業内容**
- LLM生成直後に `subv_engine.plan_schedule(target_eps, start_ep)` 呼び出し
- 各 `ArcBlueprint` の各話数に `subv_engine.apply_to_arc(arc, ep)` 呼び出し
- `arc.thematic_milestone` と動的属性 `arc.subversion` に注入されることを確認

**受け入れ基準**: 生成された `ArcList` の各アークに `thematic_milestone` が「【裏切り-X】...」形式で含まれる

**テスト作成**: `tests/test_planning_agent.py::test_generate_arcs_with_subversion`

---

## Step 8: `generate_arcs()` 戻り値にエンジン状態を含める

**作業内容**
- `artifacts` に `"subversion_engine": subv_engine.model_dump()` を追加
- `ArcList` 返却はそのまま（互換性維持）

**受け入れ基準**: `artifacts["subversion_engine"]["schedule"]` に13件のスケジュールが含まれる

---

## Step 9: `generate_commercial_beat_sheet()` で Beat へ適用

**作業内容**
- 同一 `SubversionEngine` インスタンス（または artifacts から復元）を使用
- 生成された `EpisodeBeat` リストの各要素に `subv_engine.apply_to_beat(beat, beat.ep_num)` 呼び出し
- `beat.mission` / `beat.visual_scene_focus` / `beat.tension_target` が更新されることを確認

**受け入れ基準**: 3の倍数話のビートで `tension_target` が +0.3 されている

**テスト作成**: `tests/test_planning_agent.py::test_beat_sheet_subversion_injection`

---

## Step 10: 設定パラメータ外部化（artifacts/kilo.json 対応）

**作業内容**
- `interval` / `enabled` / `pattern_weights` / `seed` を artifacts から読み取り
- `enabled=False` の場合はスケジュール生成・適用をスキップ
- `kilo.json` の `planning.subversion` セクションからも読めるように `PromptManager` 経由で渡せる仕組み確認

**受け入れ基準**: `enabled=False` で裏切り注入が一切行われない

**テスト作成**: `tests/test_planning_agent.py::test_subversion_disabled`

---

## Step 11: 統合テスト・エンドツーエンド確認

**作業内容**
- `PlanningAgent.execute()` をモック LLM で実行し、全フロー（Arc生成→Beat生成）で裏切りが一貫して適用されることを確認
- `validate_coherence()` がエラーを出さないことを確認

**受け入れ基準**: `pytest tests/test_planning_integration.py::test_full_subversion_flow -v` が通る

---

## Step 12: ドキュメント更新・リグレッションテストスイート追加

**作業内容**
- `README.md` または `docs/architecture/subversion_engine.md` に仕様・設定・拡張方法を記載
- 既存全テストスイート `pytest tests/ -x --tb=short` を実行し、リグレッションなしを確認
- CI用に `tests/test_subversion_regression.py` を作成（全ステップの要点をカバー）

**受け入れ基準**: 全テスト通過。ドキュメントが存在する。

---

## 依存関係グラフ

```
Step 1 → Step 2,3
Step 4 → Step 5
Step 1,4 → Step 6
Step 6 → Step 7 → Step 8
Step 7 → Step 9
Step 6 → Step 10
Step 7,9,10 → Step 11
Step 11 → Step 12
```

## 並行実行可能グループ
- Group A: Step 1, 4 (独立)
- Group B: Step 2, 3 (Step 1 後)
- Group C: Step 5 (Step 4 後)
- Group D: Step 6, 7, 8, 9, 10 (順序制約あり)
- Group E: Step 11, 12 (全前提後)