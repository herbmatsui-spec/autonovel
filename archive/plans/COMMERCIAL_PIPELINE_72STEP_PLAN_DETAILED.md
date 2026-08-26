# 72ステップ詳細実装計画書：CommercialPipeline完全実装 & 残タスク解消

**作成日**: 2026-07-13
**対象**: `src/backend/workflows/commercial_pipeline.py` および関連テスト群
**目的**: 低性能LLMでも確実に実装可能な粒度（1ステップ30分以内）に細分化し、CommercialPipeline を完全稼働させる
**前提**: 以下の修正は既に完了済み
- `CommercialPipeline.__init__(csv_path)` の導入
- `_create_schedule_csv` の `self.csv_path` 利用化
- `_generate_content` の動的 `book_id` 取得
- `PipelineError`例外階層の確立

---

## 概要表

| フェーズ | ステップ範囲 | テーマ | 推定時間 |
|---------|------------|--------|----------|
| Phase 1 | 1-8 | 残タスク：step_planエラー処理テスト修正 | 2-3時間 |
| Phase 2 | 9-16 | CommercialPipeline構造分析と文書化 | 2-3時間 |
| Phase 3 | 17-28 | 例外・リトライ機構の強化とテスト | 3-4時間 |
| Phase 4 | 29-40 | CSV出力とexports構造の安定化 | 3-4時間 |
| Phase 5 | 41-52 | 動的book_idとDB統合の完全実装 | 3-4時間 |
| Phase 6 | 53-64 | モック戦略とテストカバレッジ強化 | 4-5時間 |
| Phase 7 | 65-72 | E2Eテスト、CI統合、最終検証 | 3-4時間 |

---

## Phase 1: 残タスク解消 — step_plan エラー処理テスト修正（ステップ1-8）

### ステップ1: 失敗テストの原因究明
- **対象ファイル**: `tests/test_commercial_pipeline_error.py`
- **アクション**:
  1. `pytest tests/test_commercial_pipeline_error.py::test_step_plan_raises_pipeline_error -v` を実行
  2. 失敗メッセージ `Failed: DID NOT RAISE PipelineError` を確認
  3. 原因（`async_retry` デコレータが例外を再送出しない可能性）を README に記録
- **完了条件**: 失敗原因が1文で記述されている
- **出力**: なし（調査のみ）

### ステップ2: async_retry デコレータの挙動確認
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py` 23-41行
- **アクション**:
  1. `async_retry` 関数を読む
  2. `attempt >= max_attempts` のとき `raise PipelineError` しているか確認
  3. 確認結果をメモする
- **完了条件**: `async_retry` が最終的に `PipelineError` を送出することを確認

### ステップ3: _step_plan_async がリトライをバイパスする問題分析
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py` 55-58行
- **アクション**:
  1. `_step_plan_async` は `_step_plan` を同期的に呼ぶだけか確認
  2. `_step_plan` は `@staticmethod` で宣言されているか確認
  3. テストは `_step_plan_async` を呼んでいるため、リトライ経由で PipelineError が送出されるべき状況を整理
- **完了条件**: 期待挙動と実際の挙動の差分を1段落で記述

### ステップ4: _step_plan に明示的バリデーション追加
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py` 71-114行
- ** SEARCH対象**（適用済み）:
  ```python
  keywords = [kw.strip() for kw in series_config.get("keywords", "") if kw.strip()]
  if not keywords:
      raise ValueError("Missing required keywords")
  ```
- **アクション**:
  1. 既に修正が適用されていることを `read_file` で確認（73-75行）
  2. 修正されていない場合は `apply_diff` で適用
- **完了条件**: 73-75行にバリデーションが存在する

### ステップ5: _step_plan の try-except が ValueError を捕捉することを確認
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py` 114-116行
- **アクション**:
  1. `except Exception as e` が `ValueError` を捕捉することを確認（Python 仕様上捕捉される）
  2. `raise PipelineError(f"Bible generation failed: {e}") from e` が実行されることを確認
- **完了条件**: 例外チェーンが `ValueError → PipelineError` になることを言語で説明可能

### ステップ6: テストをパスする最小限の修正
- **対象ファイル**: `tests/test_commercial_pipeline_error.py` 37-46行（test_step_plan_raises_pipeline_error）
- **アクション**:
  1. テストの `invalid_config = {"invalid": "config"}` を確認
  2. この config は `keywords` キーを持たないため、`series_config.get("keywords", "")` は空文字列を返す
  3. `if not keywords:` が `True` になり `ValueError` が送出されることを確認
- **完了条件**: ロジックが通ることをトレースで説明可能

### ステップ7: テスト実行と検証
- **アクション**:
  1. `pytest tests/test_commercial_pipeline_error.py::test_step_plan_raises_pipeline_error -v` を実行
  2. PASSED を確認
  3. 失敗している場合は `async_retry` が `PipelineError` を再ラップしているか確認
- **完了条件**: テスト1件が PASSED

### ステップ8: 全エラーテストの実行と確認
- **アクション**:
  1. `pytest tests/test_commercial_pipeline_error.py -v` を実行
  2. 2件とも PASSED を確認
  3. 失敗している場合はステップ2に戻り原因究明
- **完了条件**: 2件のテストが PASSED

---

## Phase 2: CommercialPipeline 構造分析と文書化（ステップ9-16）

### ステップ9: commercial_pipeline.py の全メソッド一覧作成
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **アクション**:
  1. クラス `CommercialPipeline` の全メソッドを列挙
  2. 各メソッドのシグネチャ・戻り値・概要を記述
- **出力**: `docs/commercial_pipeline_methods.md`

### ステップ10: _step_plan の Bible 構造仕様書作成
- **アクション**:
  1. `_step_plan` が返す `bible_data` 辞書の全キーを列挙
  2. 各キーの型・用途を記述
- **出力**: `docs/bible_data_structure.md`

### ステップ11: _generate_content の context 構造仕様書作成
- **アクション**:
  1. `_generate_content` が `EpisodeWriter.write` に渡す `context` 辞書を列挙
  2. 全キーと `EpisodeWriter` が期待するキーの対応表を作成
- **出力**: `docs/episode_context_structure.md`

### ステップ12: exports 辞書の構造仕様書作成
- **アクション**:
  1. `_generate_content` が返す `exports` の構造（platform -> List[episode]）を記述
  2. 各 episode 辞書のキー一覧を作成
- **出力**: `docs/exports_structure.md`

### ステップ13: CSV 出力フォーマット仕様書作成
- **アクション**:
  1. `_create_schedule_csv` が書き込む CSV のヘッダーを記述
  2. 各カラムの型・値域を記述
- **出力**: `docs/csv_format.md`

### ステップ14: run メソッドの制御フロー図作成
- **アクション**:
  1. `run` メソッドの開始→Bible 生成→コンテンツ生成→CSV 作成→終了を Mermaid 記法で図示
- **出力**: `docs/commercial_pipeline_flow.md`

### ステップ15: PipelineError 例外階層図の更新
- **対象ファイル**: `src/core/exceptions.py`
- **アクション**:
  1. `HegemonyError → PipelineError` の継承関係を確認
  2. 図を更新
- **出力**: `docs/exception_hierarchy_updated.md`

### ステップ16: 依存モジュール一覧の作成
- **アクション**:
  1. `commercial_pipeline.py` が依存するモジュール（EpisodeWriter, PipelineError 等）を列挙
- **出力**: `docs/commercial_pipeline_deps.md`

---

## Phase 3: 例外・リトライ機構の強化とテスト（ステップ17-28）

### ステップ17: async_retry のユニットテスト追加（正常系）
- **対象**: `tests/test_commercial_pipeline_unit.py`
- **アクション**:
  1. `async_retry(max_attempts=3)` を通じて1回目で成功する関数のテストを追加
- **完了条件**: テストが PASSED

### ステップ18: async_retry のユニットテスト追加（リトライ全失敗）
- **アクション**:
  1. 常に `RuntimeError` を送出する関数をデコレート
  2. 3回リトライ後に `PipelineError` が送出されることを検証
- **完了条件**: テストが PASSED

### ステップ19: async_retry のユニットテスト追加（2回目で成功）
- **アクション**:
  1. 1回目は失敗、2回目は成功するモック関数を作成
  2. 2回目の戻り値が返されることを検証
- **完了条件**: テストが PASSED

### ステップ20: ジッタ計算の検証テスト追加
- **アクション**:
  1. `jitter = delay * 0.1 * random.uniform(0.5, 1.5)` の計算が想定範囲内であることを検証
  2. `random.seed` を固定して決定論的テストを作成
- **完了条件**: ジッタ値が [0.5, 1.5] 倍の範囲内であることを検証

### ステップ21: PipelineError の属性テスト追加
- **対象**: `src/core/exceptions.py` 48-63行
- **アクション**:
  1. `PipelineError(message, original, status_code, error_code)` のコンストラクタ検証
  2. 各属性が保持されることを検証
- **完了条件**: テストが PASSED

### ステップ22: PipelineError の属性アクセス修正
- **アクション**:
  1. 現状の `super().__init__(message, original, status_code, error_code)` では属性アクセス不可
  2. `self.original = original`, `self.status_code = status_code`, `self.error_code = error_code` を追加
- **対象ファイル**: `src/core/exceptions.py`
- **変更イメージ**:
  ```python
  def __init__(self, message, original=None, status_code=502, error_code="COMMERCIAL_PIPELINE_ERROR"):
      super().__init__(message)
      self.original = original
      self.status_code = status_code
      self.error_code = error_code
  ```
- **完了条件**: 属性アクセス可能

### ステップ23: PipelineError の str(message) 検証テスト追加
- **アクション**:
  1. `str(PipelineError("test"))` が `"test"` になることを検証
- **完了条件**: テストが PASSED

### ステップ24: HegemonyError 基底クラスのテスト追加
- **アクション**:
  1. `PipelineError` が `HegemonyError` のインスタンスでもあることを検証（`isinstance`）
- **完了条件**: テストが PASSED

### ステップ25: リトライ時の logger.warning 出力のモック検証
- **アクション**:
  1. `unittest.mock.patch("src.backend.workflows.commercial_pipeline.logger")` でロガーをモック
  2. `warning` が呼ばれたことを検証
- **完了条件**: テストが PASSED

### ステップ26: リトライ時の asyncio.sleep をモック化
- **アクション**:
  1. `patch("asyncio.sleep")` でスリープを即時復帰させ、テスト時間を短縮
- **完了条件**: テストが高速実行（1秒未満）で PASSED

### ステップ27: _step_plan の正常系テスト追加
- **アクション**:
  1. 有効な `series_config` を渡して `_step_plan` が正しい `bible_data` を返すことを検証
- **完了条件**: bible_data の主要キーがすべて存在

### ステップ28: _step_plan の境界値テスト追加
- **アクション**:
  1. `target_eps=0`, `keywords=[""]`, `platforms=[]` 等の境界値での挙動を検証
- **完了条件**: 想定通りの振る舞い

---

## Phase 4: CSV出力とexports構造の安定化（ステップ29-40）

### ステップ29: _create_schedule_csv の正常系テスト追加
- **アクション**:
  1. 仮の `exports` を渡し、CSV が指定パスに書き込まれることを検証
  2. `csv_path` に一時ファイルを指定
- **完了条件**: ファイルが作成され、内容が期待通り

### ステップ30: _create_schedule_csv の異常系テスト追加（権限エラー）
- **アクション**:
  1. 書込み権限のないパス（`/root/forbidden.csv` 等）を指定
  2. `PipelineError` が送出されることを検証
- **完了条件**: テストが PASSED

### ステップ31: CSV ヘッダーの定数化
- **アクション**:
  1. CSV ヘッダー文字列をモジュール定数 `CSV_HEADER` として切り出し
- **完了条件**: 定数参照に切り替わる

### ステップ32: CSV 行生成ロジックの関数化
- **アクション**:
  1. `_csv_row(platform, episode) -> str` 関数を抽出
  2. 両パスで同じロジックを使うようリファクタ
- **完了条件**: 関数が抽出され、テスト通過

### ステップ33: exports 構築時の platform 繰り返し処理を別メソッドへ抽出
- **対象**: `commercial_pipeline.py` 209-218行
- **アクション**:
  1. `_append_to_exports(exports, platform, episode_entry)` メソッドを抽出
- **完了条件**: メソッド分割とテスト通過

### ステップ34: exports が空の場合のテスト追加
- **アクション**:
  1. `exports = {}` で `_create_schedule_csv` を呼び出し
  2. ヘッダーのみの CSV が生成されることを検証
- **完了条件**: テストが PASSED

### ステップ35: 同一 platform への複数 episode 追加テスト
- **アクション**:
  1. 1つの platform に10件の episode を追加し、exports が正しく構築されることを検証
- **完了条件**: テストが PASSED

### ステップ36: 複数 platform の混在テスト
- **アクション**:
  1. `["kakuyomu", "narou", "novelup"]` の3プラットフォームで exports を構築し検証
- **完了条件**: テストが PASSED

### ステップ37: CSV 改行コードの確定
- **アクション**:
  1. 現状 `csv_content += "...\n"` の `\n` を使用。LF に統一。
  2. 仕様書 `docs/csv_format.md` の記載と照合
- **完了条件**: 改行コードが確定

### ステップ38: CSV エスケープ処理の検証
- **アクション**:
  1. タイトルにカンマが含まれる場合の挙動を確認
  2. 必要なら `csv.writer` に切り替え
- **完了条件**: カンマ含みタイトルでも崩壊しない

### ステップ39: csv.writer への移行（任意）
- **アクション**:
  1. 現状の文字列結合から `csv.writer` に切り替え、クォーティング対応
- **完了条件**: 移行後テストが通る、または後続へ移行を判断

### ステップ40: CSV 出力の統合テスト追加
- **アクション**:
  1. `CommercialPipeline().run()` の後に CSV が生成されることを検証する統合テストを追加
- **完了条件**: 統合テストが PASSED

---

## Phase 5: 動的book_idとDB統合の完全実装（ステップ41-52）

### ステップ41: book_id の取得ロジック仕様化
- **アクション**:
  1. `bible.get("book_id", series_config.get("book_id", 1))` のフォールバック順序を文書化
- **出力**: `docs/book_id_resolution.md`

### ステップ42: book_id 取得のユニットテスト追加
- **アクション**:
  1. `bible` に `book_id` がある場合、優先されることを検証
  2. `series_config` にのみある場合のフォールバックを検証
  3. 両方にない場合、`1` になることを検証
- **完了条件**: 3つのテストが PASSED

### ステップ43: EpisodeWriter.write のシグネチャ確認
- **対象ファイル**: `src/services/episode_writer.py`
- **アクション**:
  1. `write(self, book_id, ep_num, context)` のシグネチャを確認
  2. 期待される `context` キー一覧を作成
- **完了条件**: EpisodeWriter 側の契約が文書化済み

### ステップ44: context 辞書の不足キー検証
- **アクション**:
  1. `commercial_pipeline.py` の `context`（165-186行）と EpisodeWriter 期待キーを照合
  2. 不足 or 過剰キーを列挙
- **完了条件**: 差分リストが完成

### ステップ45: context 不足キーの補完
- **アクション**:
  1. 不足キーがあればデフォルト値を補完
- **完了条件**: 差分リストが0件

### ステップ46: 前話コンテキストの永続化設計
- **アクション**:
  1. `previous_episode_context` をメモリからではなくDBから取得する設計を検討
  2. 設計ドキュメント作成
- **出力**: `docs/previous_episode_context_design.md`

### ステップ47: EpisodeResult のキー整合性確認
- **対象**: `src/models/production_config.py` `EpisodeResult`
- **アクション**:
  1. `EpisodeWriter.write` の戻り値と `_generate_content` の `episode_entry` のキーを照合
- **完了条件**: キー一覧が整合

### ステップ48: result.get("text") と EpisodeResult.content の対応確認
- **アクション**:
  1. `result.get("text", "")` が `EpisodeResult.content` に対応するか確認
  2. 不整合なら修正
- **完了条件**: フィールド名が一致

### ステップ49: quality_score の数値検証テスト
- **アクション**:
  1. `quality_score` が 0.0-1.0 に収まることを検証
- **完了条件**: テストが PASSED

### ステップ50: killer_phrase フィールドのnull許容確認
- **アクション**:
  1. `killer_phrase` が空文字 or None の場合の挙動を検証
- **完了条件**: null 安全

### ステップ51: episode_entry のキー不変テスト追加
- **アクション**:
  1. 戻り値の各 episode 辞書が指定キーを持つことを検証
- **完了条件**: テストが PASSED

### ステップ52: 動的 book_id とDB 統合の設計レビュー
- **アクション**:
  1. Phase 5 の成果をレビュー
  2. DB から book_id を引く方式（HistoryRepo 経由等）を決定
- **出力**: `docs/book_id_db_strategy.md`

---

## Phase 6: モック戦略とテストカバレッジ強化（ステップ53-64）

### ステップ53: テスト用モック EpisodeWriter の作成
- **出力**: `tests/mocks/mock_episode_writer.py`
- **アクション**:
  1. `EpisodeWriter` を継承した `MockEpisodeWriter` を作成
  2. `write` を固定値を返すようオーバーライド
- **完了条件**: モックがimport可能

### ステップ54: pytest.fixture でモックを注入
- **対象**: `tests/test_commercial_pipeline_unit.py`
- **アクション**:
  1. `@pytest.fixture` で `mock_writer` を提供
- **完了条件**: テストでモックが利用可能

### ステップ55: patch.object から fixture モックへの段階移行
- **アクション**:
  1. `with patch.object(...)` の代わりに fixture を使用するようテストを修正
- **完了条件**: テストが PASSED

### ステップ56: テスト用 bible フィクスチャの作成
- **対象**: `tests/conftest.py` または既存モジュール
- **アクション**:
  1. `dummy_bible` を共通フィクスチャとして切り出し
- **完了条件**: 重複が解消

### ステップ57: テスト用 series_config フィクスチャの作成
- **アクション**:
  1. 有効な `series_config` 辞書を共通フィクスチャ化
- **完了条件**: 重複が解消

### ステップ58: unittest.mock.patch の使い方を共通モックへ移行
- **アクション**:
  1. `@patch("src.services.episode_writer.EpisodeWriter.write")` を `MockEpisodeWriter` へ置換
- **完了条件**: テストが PASSED

### ステップ59: _generate_content 正常系テストの拡充
- **アクション**:
  1. 5話生成の正常系テストを追加
- **完了条件**: テストが PASSED

### ステップ60: _generate_content 異常系テストの拡充
- **アクション**:
  1. 2話目の `writer.write` が失敗するケースを追加
  2. `PipelineError` が即時に送出されることを検証
- **完了条件**: テストが PASSED

### ステップ61: _step_plan 例外メッセージ内容検証テスト
- **アクション**:
  1. `str(exc_info.value)` に `"Bible generation failed"` が含まれることを検証
- **完了条件**: テストが PASSED

### ステップ62: run メソッドの正常系テスト追加
- **アクション**:
  1. `run` 全体を通す正常系テスト（モック使用）
- **完了条件**: テストが PASSED

### ステップ63: run メソッドの異常系テスト追加
- **アクション**:
  1. `_step_plan_async` で失敗した場合 `run` が `"error"` キーを持つことを検証
- **完了条件**: テストが PASSED

### ステップ64: test_run_handles_pipeline_error_gracefully の挙動確認
- **対象**: `tests/test_commercial_pipeline_unit.py` 67-77行
- **アクション**:
  1. 既存テストが `patch.object(pipeline, "run", ...)` を使っているか確認
  2. 挙動が妥当ならそのまま、不自然なら修正
- **完了条件**: テストが PASSED

---

## Phase 7: E2Eテスト、CI統合、最終検証（ステップ65-72）

### ステップ65: E2Eテストの設計
- **アクション**:
  1. API → パイプライン起動 → ポーリング → 完了までのフローを設計
- **出力**: `docs/e2e_test_design.md`

### ステップ66: E2Eテストのスケルトン作成
- **出力**: `tests/test_commercial_end_to_end.py` 拡充
- **アクション**:
  1. `test_commercial_pipeline_end_to_end` の骨組みを整える
- **完了条件**: テストが実行可能（SKIPでも可）

### ステップ67: E2Eテストのモック版実装
- **アクション**:
  1. HTTP クライアントと DB をモック化した E2E テストを実装
- **完了条件**: モック版 E2E が PASSED

### ステップ68: CIワークフローへの test_commercial_pipeline_error 追加
- **対象**: `.github/workflows/ci.yml`（存在確認）
- **アクション**:
  1. テスト対象リストに `tests/test_commercial_pipeline_error.py` を追加
- **完了条件**: CI 設定に追加

### ステップ69: pyproject.toml の ruff/mypy 設定確認
- **アクション**:
  1. `commercial_pipeline.py` が `ruff check` を通ることを確認
  2. mypy の `tuple` → `Tuple` 等の警告に対応
- **完了条件**: リンタが通過

### ステップ70: CommercialPipeline 関連テストの一括実行
- **アクション**:
  1. `pytest tests/test_commercial_pipeline_error.py tests/test_commercial_pipeline_unit.py -v` を実行
  2. 全 PASSED を確認
- **完了条件**: 全テスト PASSED

### ステップ71: 最終カバレッジレポート生成
- **アクション**:
  1. `pytest --cov=src/backend/workflows/commercial_pipeline tests/` を実行
  2. カバレッジ80%以上を確認
- **完了条件**: カバレッジ80%以上

### ステップ72: 全ステップ完了をマーク
- **アクション**:
  1. 本計画書の進捗表をすべて `[x]` に更新
  2. COMMERCIAL_PIPELINE_72STEP_PLAN_DETAILED.md の最後に署名と完了日を記録
- **完了条件**: 全ステップが `[x]` になる

---

## 完了条件チェックリスト

### Phase 1（残タスク解消）
- [ ] test_step_plan_raises_pipeline_error が PASSED
- [ ] test_generate_content_raises_pipeline_error_on_episode_write が PASSED
- [ ] tests/test_commercial_pipeline_error.py 全件 PASSED

### Phase 2（構造文書化）
- [ ] commercial_pipeline.py の全メソッドが文書化済み
- [ ] bible_data 構造が文書化済み
- [ ] episode.context 構造が文書化済み
- [ ] exports 構造が文書化済み
- [ ] CSV フォーマットが文書化済み

### Phase 3（例外・リトライ強化）
- [ ] async_retry の正常系・リトライ全失敗・部分成功テストが PASSED
- [ ] PipelineError の属性が保持される
- [ ] PipelineError が HegemonyError のサブクラス
- [ ] asyncio.sleep がモック化済み

### Phase 4（CSV 出力安定化）
- [ ] CSV 正常系・異常系テストが PASSED
- [ ] CSV ヘッダーが定数化
- [ ] exports 構築がメソッド分割済み
- [ ] カンマ含みタイトルで崩壊しない

### Phase 5（動的 book_id と DB 統合）
- [ ] book_id 取得ロジックが文書化済み
- [ ] フォールバック順序のテストが PASSED
- [ ] EpisodeWriter.write 契約が文書化済み
- [ ] context の過不足が解消
- [ ] EpisodeResult と episode_entry のキーが整合

### Phase 6（モック戦略）
- [ ] MockEpisodeWriter が作成済み
- [ ] fixture が整備済み
- [ ] patch から fixture へ移行済み
- [ ] _generate_content の正常・異常系テスト拡充
- [ ] run の正常・異常系テスト拡充

### Phase 7（E2E・CI）
- [ ] E2E 設計書が完成
- [ ] E2E モック版テストが PASSED
- [ ] CI ワークフローにテスト追加済み
- [ ] ruff/mypy が通過
- [ ] 全テストが PASSED
- [ ] カバレッジ80%以上

---

## リスクと注意事項

1. **step_plan のテストが通らない**: ステップ1-8を順に実行すれば解決する。`if not keywords: raise ValueError` と `except Exception` が連鎖すれば `PipelineError` になる。
2. **PipelineError の属性アクセス**: 現状 `super().__init__(message, original, status_code, error_code)` では属性アクセス不可。ステップ22で修正。
3. **asyncio.sleep のモック化忘れ**: リトライテストが数秒かかるため必ずステップ26でモック化する。
4. **DB 副作用**: テストで実際のDBを使用しない。モック or 一時ファイルで代用。
5. **低性能 LLM の壁**: 各ステップは30分以内、1ファイル編集で完了する粒度。不明点があればそのステップをさらに分割する。

---

## 推定スケジュール

| Phase | ステップ | 推定時間 | 備考 |
|-------|---------|----------|------|
| Phase 1 | 1-8 | 2-3時間 | 残タスク即時解消 |
| Phase 2 | 9-16 | 2-3時間 | 文書化のみ |
| Phase 3 | 17-28 | 3-4時間 | テスト追加中心 |
| Phase 4 | 29-40 | 3-4時間 | CSV 安定化 |
| Phase 5 | 41-52 | 3-4時間 | 契約整合 |
| Phase 6 | 53-64 | 4-5時間 | モック戦略 |
| Phase 7 | 65-72 | 3-4時間 | E2E・CI |
| **合計** | **1-72** | **20-27時間** | |

---

## ステップ実行記録

| ステップ | 実行日 | 実行者 | 結果 | 備考 |
|---------|--------|--------|------|------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | 2026-07-13 | Zoo（適用済み） | 完了 | `_step_plan` にバリデーション追加済 |
| ... | | | | |
| 72 | | | | |
