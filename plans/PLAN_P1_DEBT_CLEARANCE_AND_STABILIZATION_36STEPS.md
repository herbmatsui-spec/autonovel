# AutoNovel 実装計画書: Phase 1 (P1)
# 負債の清算と基盤の安定化 (36 Steps)

**目的**: 現行テストスイートの全失敗・エラー（56件）を100%解消し、非推奨コードのパージ、Google GenAI SDKの一本化、形骸化スタブの整理を完了して強固な土台を回復する。  
**対象読者**: 小型・低性能LLM（Small LLM / 7Bクラス等）でも迷わず1ステップずつ順次実行できるように、ファイルパス、修正内容、テストケース名、検証コマンドを厳密に定義。

---

## 📋 全体構成（36ステップ）

- **Part 1 (Step 1-8)**: Pydanticモデル変更へのテスト追従・Bit Rot解消
- **Part 2 (Step 9-14)**: Publisher・外部連携テストの環境非依存化（モック修復）
- **Part 3 (Step 15-20)**: 非同期DB・トランザクション・WebSocket並行性テスト修復
- **Part 4 (Step 21-26)**: 非推奨 `age_client.py` の完全安全削除と参照切替
- **Part 5 (Step 27-31)**: Google GenAI SDK（新旧混在）の完全一本化
- **Part 6 (Step 32-36)**: スタブ・空実装の正規化とP1総合回帰検証

---

## Part 1: Pydanticモデル変更へのテスト追従・Bit Rot解消 (Step 1-8)

### Step 1: `EroticCurve` クラスのコンストラクタ互換性の修正
- **目的**: 引数なし初期化 `EroticCurve()` で `TypeError` が発生する問題を修正。
- **対象ファイル**: `src/agents/erotic_enhancer.py` または `src/models/erotic.py`
- **変更内容**: `EroticCurve` の `points: list[Any] = Field(default_factory=list)` または `def __init__(self, points: list[Any] | None = None, ...)` のように、デフォルト引数を持たせて引数なし初期化を許容する。
- **検証テスト**: `tests/unit/agents/test_erotic_pipeline.py::TestEroticCurve::test_curve_creation`
- **実行コマンド**: `pytest tests/unit/agents/test_erotic_pipeline.py -k "TestEroticCurve"`

### Step 2: `TestEroticCurve` 単体テストの完全パス確認
- **目的**: `test_add_point`, `test_get_phase_intensity`, `test_curve_validation_u_shape` を修正・通過させる。
- **対象ファイル**: `tests/unit/agents/test_erotic_pipeline.py`
- **変更内容**: `curve = EroticCurve()` で生成したインスタンスへの `add_point` 呼び出しが正常に動作することを確認。
- **検証テスト**: `TestEroticCurve` の全4テスト
- **実行コマンド**: `pytest tests/unit/agents/test_erotic_pipeline.py -k "TestEroticCurve"`

### Step 3: `CharacterStateSnapshot` モデルのスキーマ修正
- **目的**: `Extra inputs are not permitted` (psychological_state, items_held, body_marks) および `Field required: episode_num` の解消。
- **対象ファイル**: `src/agents/erotic/` または `src/models/` 内の `CharacterStateSnapshot` 定義
- **変更内容**:
  1. `episode_num: int = 1` にデフォルト値を設定。
  2. `psychological_state: str = ""`、`items_held: list[str] = Field(default_factory=list)`、`body_marks: list[str] = Field(default_factory=list)` をモデルに追加、または `model_config = ConfigDict(extra="ignore")` を設定。
- **検証テスト**: `tests/unit/agents/test_erotic_pipeline.py::TestCharacterStateSnapshot`
- **実行コマンド**: `pytest tests/unit/agents/test_erotic_pipeline.py -k "TestCharacterStateSnapshot"`

### Step 4: `ContinuityTracker` のインターフェース復元
- **目的**: `AttributeError: 'ContinuityTracker' object has no attribute 'update_character_state'` を修正。
- **対象ファイル**: `src/agents/erotic/` または `src/agents/` の `ContinuityTracker` クラス
- **変更内容**: 内部でリネームされた更新メソッドへの委譲ラッパーとして `def update_character_state(self, character_name: str, state: Any, ...) -> None:` を追加。
- **検証テスト**: `tests/unit/agents/test_erotic_pipeline.py::TestContinuityTracker::test_update_and_get_character_state`
- **実行コマンド**: `pytest tests/unit/agents/test_erotic_pipeline.py -k "TestContinuityTracker"`

### Step 5: `ContinuityTracker` の全バリデーションメソッドの整合
- **目的**: `stamina_transition_validation`, `invalid_stamina_transition`, `intimacy_progression` などのテスト通過。
- **対象ファイル**: `ContinuityTracker` 実装クラス
- **変更内容**: トラッカー内の状態遷移ルールチェック関数（スタミナ減少・親密度増加）のシグネチャをテストの呼び出し形式に適合させる。
- **検証テスト**: `TestContinuityTracker` の全テストケース
- **実行コマンド**: `pytest tests/unit/agents/test_erotic_pipeline.py -k "TestContinuityTracker"`

### Step 6: `ContinuityReport` モデルの修復
- **目的**: `TestContinuityReport` (test_report_creation, test_report_with_issues) のエラー解消。
- **対象ファイル**: `src/agents/erotic_integrity.py` または関連モデル
- **変更内容**: `ContinuityReport` のコンストラクタで受け取る引数（`issues: list`, `score: float` 等）の初期値を設定。
- **検証テスト**: `tests/unit/agents/test_erotic_pipeline.py::TestContinuityReport`
- **実行コマンド**: `pytest tests/unit/agents/test_erotic_pipeline.py -k "TestContinuityReport"`

### Step 7: `EroticIntegrityChecker` および統合パイプラインテスト修復
- **目的**: `TestEroticIntegrityChecker` と `TestEroticPipelineIntegration` の3テストのパス。
- **対象ファイル**: `tests/unit/agents/test_erotic_pipeline.py`
- **変更内容**: パイプライン呼び出し時のコンテキスト辞書に必須のキー（`consent: bool = True` 等）を補完。
- **検証テスト**: `TestEroticIntegrityChecker`, `TestEroticPipelineIntegration`
- **実行コマンド**: `pytest tests/unit/agents/test_erotic_pipeline.py -k "Integration or Integrity"`

### Step 8: `test_erotic_baseline.py` のセットアップエラー解消
- **目的**: `TypeError` による setup エラー（2件）を解消。
- **対象ファイル**: `tests/unit/test_erotic_baseline.py`
- **変更内容**: テストフィクスチャで渡している引数の型不整合（整数・浮動小数点数）を修正。
- **検証テスト**: `tests/unit/test_erotic_baseline.py`
- **実行コマンド**: `pytest tests/unit/test_erotic_baseline.py`

---

## Part 2: Publisher・外部連携テストの環境非依存化 (Step 9-14)

### Step 9: Selenium WebDriver初期化の安全なモック構造化
- **目的**: ローカルChromeドライバ不在時にテストが `ERROR` になるのを防止。
- **対象ファイル**: `tests/unit/publishers/test_narou.py`
- **変更内容**: `publisher` フィクスチャで `selenium.webdriver.Chrome` のインスタンス化を完全にインターセプトし、実ブラウザ探索をバイパス。
- **検証テスト**: `tests/unit/publishers/test_narou.py::TestNarouPublisher::test_publisher_initialization`
- **実行コマンド**: `pytest tests/unit/publishers/test_narou.py -k "test_publisher_initialization"`

### Step 10: `TestNarouPublisher.test_authenticate_*` のモック修復
- **目的**: なろう認証テスト（成功、資格情報欠落、リダイレクト失敗）の修復。
- **対象ファイル**: `tests/unit/publishers/test_narou.py`
- **変更内容**: `WebDriverWait.until()` の戻り値として `mock_element` を正しく返却するようパッチ。
- **検証テスト**: `test_authenticate_success`, `test_authenticate_missing_credentials`, `test_authenticate_failed_redirect`
- **実行コマンド**: `pytest tests/unit/publishers/test_narou.py -k "authenticate"`

### Step 11: `TestNarouPublisher.test_publish_*` のエピソード投稿修復
- **目的**: `test_publish_first_episode`, `test_update_chapter`, `test_get_post_status` の修復。
- **対象ファイル**: `tests/unit/publishers/test_narou.py`
- **変更内容**: ページ遷移URL判定ロジック（`mypage.syosetu.com`）のモック値を調整。
- **検証テスト**: `test_publish_first_episode`, `test_update_chapter`, `test_get_post_status`
- **実行コマンド**: `pytest tests/unit/publishers/test_narou.py -k "publish or chapter or status"`

### Step 12: なろう本文フォーマッタのルビ保持テスト修復
- **目的**: `test_format_for_narou`, `test_format_preserves_ruby` のパス。
- **対象ファイル**: `src/services/publishers/narou.py`
- **変更内容**: 青空文庫形式ルビ `｜漢字《かんじ》` から なろう形式 `|漢字《かんじ》` への変換正規表現をテスト期待値に合致させる。
- **検証テスト**: `test_format_for_narou`, `test_format_preserves_ruby`
- **実行コマンド**: `pytest tests/unit/publishers/test_narou.py -k "format"`

### Step 13: カクヨムPublisherテストの健全性確認
- **目的**: カクヨム側テストスイートが正常にパスすることを確認。
- **対象ファイル**: `tests/unit/publishers/test_kakuyomu.py`
- **変更内容**: APIトークンヘッダーの検証ロジック確認。
- **検証テスト**: `tests/unit/publishers/test_kakuyomu.py`
- **実行コマンド**: `pytest tests/unit/publishers/test_kakuyomu.py`

### Step 14: Publisher テストスイート全体のグリーン確認
- **目的**: `tests/unit/publishers/` 配下の全テストが 0 failed, 0 error となることを確認。
- **検証テスト**: `tests/unit/publishers/`
- **実行コマンド**: `pytest tests/unit/publishers/`

---

## Part 3: 非同期DB・トランザクション・並行性テスト修復 (Step 15-20)

### Step 15: `test_uow_repositories.py` の NameError 解消
- **目的**: `test_uow_all_repositories_instantiate_without_name_error` および `cleanup_clears_repo_cache` の修復。
- **対象ファイル**: `src/backend/database/uow.py`
- **変更内容**: インポート漏れまたはタイポによる未定義リポジトリ参照を修正。
- **検証テスト**: `tests/unit/test_uow_repositories.py`
- **実行コマンド**: `pytest tests/unit/test_uow_repositories.py`

### Step 16: `test_repository_concurrency.py` の SQLite ロック競合解消
- **目的**: `test_repository_get_set_state_async` の非同期並行実行時の `sqlite3.OperationalError: database is locked` を解消。
- **対象ファイル**: `tests/unit/test_repository_concurrency.py`
- **変更内容**: テスト用データベースURLに `sqlite+aiosqlite:///:memory:?cache=shared` または `NullPool` を適用。
- **検証テスト**: `tests/unit/test_repository_concurrency.py`
- **実行コマンド**: `pytest tests/unit/test_repository_concurrency.py`

### Step 17: `test_sqlite_rag_embedding.py` のバッチ検索修復
- **目的**: `test_sqlite_rag_batch_vector_search_and_no_truncation`, `test_backfill_missing_embeddings` の修復。
- **対象ファイル**: `tests/unit/test_sqlite_rag_embedding.py`
- **変更内容**: モックエンベディング関数の次元数（例: 768 or 1536）の不整合を修正。
- **検証テスト**: `tests/unit/test_sqlite_rag_embedding.py`
- **実行コマンド**: `pytest tests/unit/test_sqlite_rag_embedding.py`

### Step 18: `test_p4_async_and_db_concurrency.py` の Redis モック修復
- **目的**: `TestTasksRouterAsyncRedis::test_get_task_status_uses_async_redis` の修復。
- **対象ファイル**: `tests/unit/test_p4_async_and_db_concurrency.py`
- **変更内容**: `aioredis` / `redis.asyncio` クライアントの `get` メソッドのコルーチンモック化。
- **検証テスト**: `tests/unit/test_p4_async_and_db_concurrency.py`
- **実行コマンド**: `pytest tests/unit/test_p4_async_and_db_concurrency.py`

### Step 19: WebSocket / SSE ストリーミングテスト修復
- **目的**: `test_pipeline_websocket.py` の `test_pipeline_websocket_and_hub`, `test_sse_pipeline_stream` のアサーション修復。
- **対象ファイル**: `tests/unit/test_pipeline_websocket.py`
- **変更内容**: イベントハブの送出メッセージ形式（JSONキー `event` / `data`）を最新仕様に同期。
- **検証テスト**: `tests/unit/test_pipeline_websocket.py`
- **実行コマンド**: `pytest tests/unit/test_pipeline_websocket.py`

### Step 20: 残存する孤立テスト（マーケティング・決済・PDCA）の修復
- **目的**: `test_marketing_ctr_router.py`, `test_editor_autosave.py`, `test_stripe_payment.py`, `test_closed_loop_pdca.py` などの個別失敗を完全解消。
- **対象ファイル**: 該当テストファイル各所
- **変更内容**: エンドポイントプレフィックス修正、Stripe Webhook署名モック更新、PDCA改善ループ収束判定閾値の調整。
- **検証テスト**: 各テスト
- **実行コマンド**: `pytest tests/unit/marketing/ tests/unit/services/test_stripe_payment.py tests/unit/test_closed_loop_pdca.py`

---

## Part 4: 非推奨 `age_client.py` の完全安全削除と参照切替 (Step 21-26)

### Step 21: 4層圧縮層（`layer2_subgraph.py`）の AGE 依存除去
- **目的**: `Layer2SubgraphExtractor` から `age_client` 引数および Apache AGE 呼び出しコードを完全に除去。
- **対象ファイル**: `src/services/compression/layer2_subgraph.py`
- **変更内容**: RDBMS のリレーショナルテーブル（`character_relations`, `foreshadowings`）またはインメモリ NetworkX グラフからの抽出のみに統一。
- **検証テスト**: `tests/unit/services/compression/test_layer2.py`
- **実行コマンド**: `pytest tests/unit/services/compression/`

### Step 22: `FourLayerCompressor` コンストラクタからの `age_client` 削除
- **目的**: `FourLayerCompressor.__init__` から不要な `age_client: Any = None` パラメータを廃止。
- **対象ファイル**: `src/services/compression/compressor.py`
- **変更内容**: `self.age_client` を廃止し、DIコンテナからの注入不要にする。
- **検証テスト**: `tests/unit/services/compression/test_compressor.py`
- **実行コマンド**: `pytest tests/unit/services/compression/test_compressor.py`

### Step 23: GraphRAG同期サービス内の AGE 参照除去
- **目的**: `src/services/graphrag_sync_service.py` および `src/services/graph/` 内の `import age_client` を全検索・除去。
- **対象ファイル**: `src/services/graphrag_sync_service.py`, `src/backend/routers/graph.py`
- **変更内容**: SQLite / PostgreSQL (pgvector) のみの実装に一本化。
- **検証テスト**: `tests/unit/test_graphrag.py`
- **実行コマンド**: `pytest tests/unit/ -k "graph"`

### Step 24: `src/services/age_client.py` 本体の安全な削除
- **目的**: 1,095行に及ぶ非推奨ファイルをリポジトリから完全削除。
- **対象ファイル**: `src/services/age_client.py`
- **変更内容**: ファイル削除。
- **検証コマンド**: `git status` で削除確認。

### Step 25: AGE依存完全排除のリグレッション防止テスト作成
- **目的**: 将来誤って `age_client` や AGE Cypher クエリが再導入されないことを保証する静的テスト。
- **対象ファイル**: `tests/regression/test_no_age_dependency.py` (新規作成)
- **テスト内容**: `src/` 配下の全 `.py` ファイルをスキャンし、`age_client` や `agtype` のインポートが 0 件であることをアサート。
- **実行コマンド**: `pytest tests/regression/test_no_age_dependency.py`

### Step 26: 圧縮・グラフ関連テストのオールグリーン確認
- **目的**: AGE 削除後のグラフ・圧縮周りのテストが全て通ることを確認。
- **検証テスト**: `tests/unit/services/compression/`, `tests/regression/test_no_age_dependency.py`
- **実行コマンド**: `pytest tests/unit/services/compression/ tests/regression/test_no_age_dependency.py`

---

## Part 5: Google GenAI SDK（新旧混在）の完全一本化 (Step 27-31)

### Step 27: `gemini_adapter.py` を新 SDK (`google.genai`) へ移行
- **目的**: `import google.generativeai as genai` を廃止し、`from google import genai` に書き換え。
- **対象ファイル**: `src/services/llm/gemini_adapter.py`
- **変更内容**:
  ```python
  from google import genai
  from google.genai import types
  self.client = genai.Client(api_key=self.api_key)
  response = await self.client.aio.models.generate_content(
      model=self.model_name,
      contents=full_prompt,
      config=types.GenerateContentConfig(...)
  )
  ```
- **検証テスト**: `tests/unit/llm/test_gemini_adapter.py`
- **実行コマンド**: `pytest tests/unit/llm/test_gemini_adapter.py`

### Step 28: ストリーミング生成（`stream_text`）の新SDK対応
- **目的**: `gemini_adapter.py` の `stream_text` を新 SDK の非同期ジェネレータへ書き換え。
- **対象ファイル**: `src/services/llm/gemini_adapter.py`
- **変更内容**: `async for chunk in await self.client.aio.models.generate_content_stream(...)` を使用。
- **検証テスト**: `tests/unit/llm/test_gemini_adapter.py::test_gemini_stream_text`
- **実行コマンド**: `pytest tests/unit/llm/test_gemini_adapter.py -k "stream"`

### Step 29: `pyproject.toml` / `requirements.txt` から旧SDK削除
- **目的**: `google-generativeai` を削除し、`google-genai>=0.8.0` のみに一本化。
- **対象ファイル**: `pyproject.toml`, `requirements.txt`
- **変更内容**: `google-generativeai` の行を削除。
- **検証コマンド**: `pip list` および `python -c "import google.genai; print('OK')"`

### Step 30: 依存パッケージ固定（`protobuf`, `google-api-core`）の制限緩和
- **目的**: バージョン競合回避のためピン留めされていた `protobuf==5.29.5` などの制約を `protobuf>=5.29.0` に緩和。
- **対象ファイル**: `pyproject.toml`, `requirements.txt`
- **変更内容**: バージョン制約の緩和と仮想環境でのインストール確認。
- **実行コマンド**: `pip check` で依存関係の衝突がないことを確認。

### Step 31: Geminiアダプタおよび画像サービス（Imagen）の統合テスト作成
- **目的**: 新SDKでテキスト生成と画像生成の双方が正常にモック・実行できることを確認。
- **対象ファイル**: `tests/unit/llm/test_unified_genai_sdk.py` (新規作成)
- **テスト内容**: `GeminiAdapter` と `ImageService` が同一の `google.genai.Client` 互換で初期化・実行できることを検証。
- **実行コマンド**: `pytest tests/unit/llm/test_unified_genai_sdk.py`

---

## Part 6: スタブ・空実装の正規化とP1総合回帰検証 (Step 32-36)

### Step 32: `ContentProcessor` の正規実装化
- **目的**: 単に引数を返すだけだった空実装に、必要最低限のサニタイズ（NFKC正規化、危険タグ除去）を実装。
- **対象ファイル**: `src/services/content_processor.py`
- **変更内容**: `unicodedata.normalize('NFKC', content)` の適用と制御文字・スクリプトタグ除去ロジックの実装。
- **検証テスト**: `tests/unit/services/test_content_processor.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/services/test_content_processor.py`

### Step 33: `NarrativeScoringService` のスタブ脱却と型安全化
- **目的**: ダミー値を返していたナラティブスコアリングサービスをPydanticバリデーション対応にする。
- **対象ファイル**: `src/services/narrative_scoring_service.py`
- **変更内容**: スコア辞書に適切な型ヒントとデフォルトスコア計算ロジックを実装。
- **検証テスト**: `tests/unit/services/test_narrative_scoring.py` (新規作成)
- **実行コマンド**: `pytest tests/unit/services/test_narrative_scoring.py`

### Step 34: カバレッジ除外リスト（`pyproject.toml`）からの解除
- **目的**: 実装を完了したファイルを `omit` リストから除外解除し、カバレッジ計測対象に戻す。
- **対象ファイル**: `pyproject.toml`
- **変更内容**: `omit` から `content_processor.py`, `narrative_scoring_service.py` を削除。
- **検証コマンド**: `pytest --cov=src.services.content_processor tests/unit/services/test_content_processor.py`

### Step 35: P1 全体回帰テスト `test_p1_stabilization.py` の作成
- **目的**: P1で修復したすべての領域（EroticCurve, Publisher, Concurrency, AGE非依存, GenAI SDK）が協調して動作することを保証。
- **対象ファイル**: `tests/regression/test_p1_stabilization.py` (新規作成)
- **テスト内容**: 5つの主要サブシステムを順次呼び出し、エラーや警告が発生しないことをアサート。
- **実行コマンド**: `pytest tests/regression/test_p1_stabilization.py`

### Step 36: 全テストスイートの実行とオールグリーン（FAILED 0）達成
- **目的**: プロジェクト全体の 2,776 件以上のテストを実行し、すべてのテストが PASS することを確認。
- **対象ファイル**: `tests/` 全体
- **実行コマンド**: `pytest -p no:cacheprovider --tb=short`
- **合格基準**: `failed=0, errors=0` を確認し、P1 を完了とする。
