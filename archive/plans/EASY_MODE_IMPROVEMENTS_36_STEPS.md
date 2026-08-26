# かんたんモード改善 36ステップ実装計画書

対象改善案:
1. **API非同期化（タスクキュー統合）** - `src/backend/server.py:305-386`
2. **エピソード構造値のプリセット完全依存化** - `src/easy_mode/bible_generator.py:40-55`

---

## Phase A: API非同期化（タスクキュー統合） - Steps 1-24

### Step 1: 現状のエンドポイントコードをバックアップ・分析
- `src/backend/server.py:305-386` の `generate_easy` 関数を読み、依存関係をリスト化
- 進捗コールバック `progress_callback` の呼び出し箇所と形式を確認
- `BackgroundReporter` / `ProgressState` の使用方法を確認

### Step 2: Huey タスク定義ファイルを作成
- `src/backend/tasks/easy_mode_tasks.py` 新規作成
- `execute_easy_mode_generation` タスク関数を定義（`@huey.task()` 装飾）
- 引数: `task_id, api_key, genre, target_episodes, config_dict` 等

### Step 3: タスク内で使用するヘルパー関数を作成
- `create_easy_mode_pipeline(engine, config)` ファクトリ関数
- `run_pipeline_with_progress(pipeline, progress_state)` 実行ラッパー
- 進捗更新を `progress_state.update_progress()` で行うよう修正

### Step 4: タスク内でのエンジン取得ロジックを分離
- `AppContainer(api_key=api_key).engine()` 呼び出しをヘルパーに移動
- API キー検証はタスク外（エンドポイント側）で実施済みとする

### Step 5: タスク完了・エラー時の後処理を実装
- 成功時: `progress_state.is_running = False`, `result_data` 設定, `_save_to_db()`
- 失敗時: `progress_state.error = str(e)`, `_save_to_db()`, ログ出力
- 既存 `refine_erotic` タスクと同一パターンで統一

### Step 6: エンドポイントをタスク投げるだけの薄い層に変更
- `generate_easy` 関数内で `validate_api_key_or_raise(req.api_key)` 実行
- `generate_task_id("easy")` で task_id 生成
- `ProgressState` 初期化（DB保存用）
- `execute_easy_mode_generation.schedule(args=(task_id, req.api_key, ...))` でキュー投入
- `{"task_id": task_id}` を即時返却

### Step 7: リクエストスキーマから PipelineConfig 作成ロジックを共通化
- `create_pipeline_config_from_request(req)` を `src/backend/task_helpers.py` へ移動
- エンドポイントとタスク双方から呼べるよう調整

### Step 8: 進捗ステージ定義を共通化
- `stage_messages` 辞書を `src/backend/task_helpers.py` または `constants.py` に移動
- タスク側でインポートして使用

### Step 9: タスク実行時の進捗コールバック実装
- タスク内で `def progress_callback(stage, current, total):` を定義
- `ProgressState` 経由で `update_progress(current, total, msg, sub_msg)` 呼び出し
- 既存 `BackgroundReporter` と同等の動作に

### Step 10: タスクモジュールのインポート・登録確認
- `src/backend/__init__.py` または `src/backend/tasks/__init__.py` でタスク公開
- Huey がタスクを認識できるか確認（`huey --app src.backend.tasks.easy_mode_tasks` 等）

### Step 11: 開発環境で Huey ワーカー起動確認
- `huey_consumer.py src.backend.tasks.easy_mode_tasks -w 1` で起動テスト
- タスクがキューに入り、実行されるかログ確認

### Step 12: 既存テスト `tests/integration/test_api.py` を非同期版に更新
- `test_api_quick_generate` を `task_id` 取得 → ポーリング待機 → 結果検証 に変更
- `test_api_health_check` はそのまま（ヘルスチェック用）

### Step 13: ポーリング用エンドポイント確認・追加
- `GET /api/tasks/{task_id}` が既存であればそれを使用
- なければ `src/backend/routers/tasks.py` に進捗取得エンドポイント追加

### Step 14: フロントエンド連携用 SSE エンドポイント追加（任意・低優先）
- `GET /api/easy_mode/progress/{task_id}` (SSE) を `src/backend/routers/easy_mode.py` 新規作成
- `ProgressState` を Server-Sent Events 形式でストリーム配信

### Step 14b: ルーター登録
- `src/backend/server.py` の `router_modules` に `"src.backend.routers.easy_mode"` 追加確認

### Step 15: フロントエンド `EasyModeDialog` の送信ハンドラ修正
- `onSubmit` で返却される `task_id` を受け取り、ポーリング/SSE 開始
- 進捗表示 UI （プログレスバー、ステージ名、現在話数）を実装

### Step 16: ストア `useEasyModeStore` に進捗状態追加
- `easyModeProgress`, `easyModeStatus`, `easyModeLogs` 等の状態追加
- ポーリング/SSE 受信時のアクション追加

### Step 17: エラーハンドリング統一
- タスク側例外を `progress_state.error` に格納
- ポーリング時にエラー検知したらフロントエンドに表示

### Step 18: タイムアウト設定調整
- `LONG_RUNNING_PATHS` から `/api/easy_mode/generate` を削除（即時返却になるため）
- タスク側は Huey の `task_retry_delay` / `task_expiration` で制御

### Step 19: レート制限適用確認
- タスク投入エンドポイントにも `rate_limit_middleware` が効くか確認
- 必要ならタスク投入レート制限を別途設定

### Step 20: ログ・トレース連携
- `TraceContext.get_trace_id()` をタスク引数に渡し、タスク内で `TraceContext.set_trace_id()`
- OpenTelemetry スパンがタスク実行にも張られるよう調整

### Step 21: 統合テストシナリオ作成
- 正常系: ジャンル指定 → task_id 取得 → 完了までポーリング → 結果検証
- 異常系: 無効 API キー → 401、キャンセル API → タスク停止、LLM エラー → エラー状態

### Step 22: ドキュメント更新
- `docs/api/easy_mode.md` (新規) に非同期 API 仕様記載
- `README.md` の API 使用例を非同期版に更新

### Step 23: 既存同期実行コードの削除・クリーンアップ
- `server.py` から `generate_easy` 内のパイプライン直接実行コード削除
- 不要になったインポート整理

### Step 24: 動作確認・リグレッションテスト
- 全ジャンルで 1 話生成テスト実行
- 同時リクエスト 3 件投入 → 全完了確認
- キャンセル動作確認

---

## Phase B: エピソード構造値のプリセット完全依存化 - Steps 25-36

### Step 25: 現状のハードコード値を全洗い出し
- `bible_generator.py:40-55` の `episode_structure.get(...)` 箇所を特定
- 対象キー: `humiliation_ep`, `trigger_ep`, `musou_start_ep`, `final_ep`, `tension_threshold`
- `catharsis_spikes`, `density_by_phase` も確認

### Step 26: プリセット側 `episode_structure` スキーマを定義・検証
- `src/presets/zarma/episode_structure/episode_structure_zarma.yaml` を基準に必須キー列挙
- 全 9 ジャンルの YAML が同一キー構造か確認（`validate_preset` で検証）

### Step 27: `validate_preset` に `episode_structure` 必須チェック追加
- `src/presets/loader.py:164-167` の `critical_keys` に `"episode_structure"` 追加
- 中身の必須サブキー（`episode_structure.humiliation_ep` 等）も検証

### Step 28: `BibleGenerator._get_preset_defaults` からデフォルト値ロジック削除
- `episode_structure` 取得後の `.get(key, default)` 形式を `.get(key)` のみに変更
- キー欠損時は `KeyError` / `ValueError` を投げるよう修正

### Step 29: `BibleGenerator.generate` 内の変数構築をプリセット直参照に変更
- `variables` 辞書の `humiliation_ep` 等を `preset["episode_structure"]["episode_structure"]["humiliation_ep"]` 直参照に
- ネスト構造に注意（`episode_structure` キーの中にさらに `episode_structure` キー）

### Step 30: 不足時の明示エラーメッセージ実装
- `KeyError` をキャッチし、`ValueError(f"Genre {genre}: episode_structure missing key 'humiliation_ep'")` を raise
- ログにジャンル名と不足キーを出力

### Step 31: 単体テスト `tests/phase1/test_phase1_preset_integration.py` 拡張
- `test_episode_structure_schema` 追加：全ジャンルで必須サブキー存在確認
- 不足 YAML で `load_preset` → `validate_preset` が適切にエラーになること確認

### Step 32: 統合テスト `tests/phase2/test_phase2_pipeline_integration.py` 更新
- `MockEngine` 使用テストで、プリセット読み込み経路を通すよう修正
- `episode_structure` キーが正しくパイプラインまで渡ること検証

### Step 33: プリセット YAML 全ジャンル分の値整合性チェック
- 各ジャンルの `humiliation_ep < trigger_ep < musou_start_ep < final_ep` 等の順序関係確認
- `tension_threshold` が 0-100 範囲内か確認
- 不整合あれば YAML 修正

### Step 34: `PlotGenerator` 側の定数依存も確認・修正
- `src/easy_mode/plot_generator.py:10` `from config.constants import EP_CLIMAX, EP_FINAL`
- これらが `target_episodes` に依存せず固定値なら、プリセットの `final_ep` / `climax_ep` 参照に変更検討

### Step 35: ドキュメント・コメント更新
- `bible_generator.py` の docstring / コメントから「デフォルト値」記述削除
- `docs/specs/fragment_map.md` 等にプリセット必須キーとして記載追加

### Step 36: 総合動作確認・リグレッションテスト
- 全 9 ジャンルで `create_series(engine, genre).run()` 実行（モックエンジン）
- Bible 生成時の変数展開が正しく行われ、テンプレートレンダリング成功すること確認
- 既存テストスイート `pytest tests/phase1 tests/phase2 -v` 全パス確認

---

## 依存関係・並列実行可能グループ

```
Phase A (API非同期化):  Step 1-24  依存: 1→2→3→4→5→6→7→8→9→10→11→12→13→14→15→16→17→18→19→20→21→22→23→24
Phase B (プリセット化): Step 25-36 依存: 25→26→27→28→29→30→31→32→33→34→35→36

並列可: Phase A と Phase B は独立して実行可能
```

## 完了基準

| 改善案 | 完了条件 |
|--------|----------|
| API非同期化 | `/api/easy_mode/generate` が即時 `task_id` 返却、ポーリング/SSE で進捗取得・結果取得可能、既存テスト全パス |
| プリセット完全依存化 | ハードコードデフォルト値が全削除、プリセット欠損時に明示エラー、全ジャンルで Bible 生成成功、既存テスト全パス |

---

## リスク・対策

| リスク | 影響 | 対策 |
|--------|------|------|
| Huey ワーカー未起動でタスクが溜まる | API は 200 返すが処理されない | 起動スクリプトにワーカー起動追加、ヘルスチェックでワーカー生存確認 |
| プリセット YAML 不整合で全ジャンル動かない | リリースブロック | Step 33 で事前検証、CI に `validate_preset` 組み込み |
| フロントエンドポーリング実装漏れ | UI がフリーズしたように見える | Step 15-16 を Phase A 完了前に着手、並行開発 |

---

## 関連ファイル一覧

### 変更対象
- `src/backend/server.py` (Step 1, 6, 18, 23)
- `src/backend/tasks/easy_mode_tasks.py` (新規, Step 2-5, 9)
- `src/backend/task_helpers.py` (Step 7, 8)
- `src/backend/routers/easy_mode.py` (新規, Step 14, 14b)
- `src/easy_mode/bible_generator.py` (Step 25-30)
- `src/presets/loader.py` (Step 27)
- `tests/integration/test_api.py` (Step 12)
- `tests/phase1/test_phase1_preset_integration.py` (Step 31)
- `tests/phase2/test_phase2_pipeline_integration.py` (Step 32)
- `frontend/src/components/dialogs/EasyModeDialog.tsx` (Step 15)
- `frontend/src/store/useEasyModeStore.ts` (Step 16)

### 参照のみ
- `src/backend/routers/tasks.py` (Step 13 確認用)
- `src/presets/*/episode_structure/*.yaml` (Step 26, 33)
- `src/easy_mode/plot_generator.py` (Step 34 確認用)