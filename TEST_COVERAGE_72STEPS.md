# テストカバレッジ向上 実装計画書（72ステップ）

> 目標: 全体カバレッジを **56% → 80%** に引き上げる。
> 想定環境: Windows + Python 3.14（pytest, pytest-cov, pytest-asyncio 導入済み）。
> 設計方針: 各ステップは **1つのファイル変更 + 1つのコマンド実行** に収め、低性能LLMでも順次適用できるよう細分化。

---

## 第0部: 前提と測定基線（ステップ1〜10）

**ステップ1**
- 対象: ターミナル
- 作業: 作業ディレクトリへ移動
- コマンド: `cd E:\sda`
- 期待: カレントディレクトリが E:\sda になる

**ステップ2**
- 対象: `pytest.ini`
- 作業: `--cov` を一時的に外す（二重計測回避）
- 変更: `addopts = -v --tb=short` にする
- 理由: `coverage run` と pytest-cov の二重起動で 0% になるのを防ぐ

**ステップ3**
- 対象: ターミナル
- コマンド: `python -m coverage run -m pytest -q > cov_run.txt 2>&1`
- 期待: 終了コード 1（一部失敗あり）で停止

**ステップ4**
- 対象: `cov_run.txt`
- 作業: 失敗数を確認
- コマンド: `Select-String -Pattern "passed|failed" cov_run.txt | Select-Object -Last 2`
- 期待: `867 passed, 82 failed, 106 skipped` 程度が表示される

**ステップ5**
- 対象: ターミナル
- コマンド: `python -m coverage report --omit="*/site-packages/*,*/dependency_injector/*,*.pyx" > cov_base.txt 2>&1`
- 期待: `cov_base.txt` に各ファイルのカバレッジが書かれる

**ステップ6**
- 対象: `cov_base.txt`
- 作業: 全体値を控える
- コマンド: `Select-String -Pattern "TOTAL" cov_base.txt`
- 期待: `TOTAL ... 56%` が表示される（基準値）

**ステップ7**
- 対象: `tests/conftest.py`
- 作業: 既存の `mock_redis_service` フィクスチャを確認
- 確認: `autouse=True` で `RedisCacheService` が `AsyncMock` に置換されていること

**ステップ8**
- 対象: `tests/conftest.py`
- 作業: `mock_llm` フィクスチャの import パスを確認
- 確認: `from tests.mocks.mock_llm import MockGeminiApiClient` が存在すること

**ステップ9**
- 対象: ターミナル
- コマンド: `python -m pytest tests/unit/test_auth_service.py -q`
- 期待: auth 関連テストが通過する（4 passed）

**ステップ10**
- 対象: `IMPLEMENTATION_PLAN.md`
- 作業: 現在の基準値（56%）を「測定基線」としてメモ欄に追記
- 理由: 後のステップで改善幅を比較するため

---

## 第1部: 失敗テスト解消のためのモック基盤（ステップ11〜25）

**ステップ11**
- 対象: `tests/conftest.py`
- 作業: DB セッションモックフィクスチャを追加
- 追加:
```python
@pytest.fixture
def mock_db_session(monkeypatch):
    from unittest.mock import AsyncMock
    sess = AsyncMock()
    sess.execute.return_value = AsyncMock()
    sess.get_session = AsyncMock(return_value=__import__('contextlib').nullcontext(sess))
    return sess
```
- 期待: 構文エラーなく保存できる

**ステップ12**
- 対象: `src/core/container/app.py`
- 作業: `AppContainer.db()` がテストでモックされるよう `monkeypatch` 対象であることを確認
- 確認: `providers.Singleton` で定義され、`monkeypatch.setattr` 可能

**ステップ13**
- 対象: `tests/conftest.py`
- 作業: `AppContainer.db` をモックに差し替える `autouse` フィクスチャ追加
- 追加:
```python
@pytest.fixture(autouse=True)
def patch_db_container(monkeypatch):
    from src.core.container import AppContainer
    from unittest.mock import AsyncMock
    fake = AsyncMock()
    fake.get_session = AsyncMock(return_value=__import__('contextlib').nullcontext(AsyncMock()))
    monkeypatch.setattr(AppContainer, 'db', lambda: fake)
```
- 期待: `test_uow.py` の `'NoneType' object` エラーが消える見込み

**ステップ14**
- 対象: ターミナル
- コマンド: `python -m pytest tests/unit/test_uow.py -q`
- 期待: 2件が pass する（またはモック不足で別エラーに変わる）

**ステップ15**
- 対象: `tests/mocks/`
- 作業: `mock_huey.py` を新規作成
- 内容: `Huey` クラスの `task` デコレータと `enqueue` を `AsyncMock` にする最小クラス
- 期待: import エラーなく読み込める

**ステップ16**
- 対象: `src/backend/tasks.py`
- 作業: `huey` オブジェクトの import パスを確認（`from huey import Huey` 等）
- 確認: テストで `monkeypatch.setattr('src.backend.tasks.huey', mock_huey)` が可能

**ステップ17**
- 対象: `tests/conftest.py`
- 作業: `mock_huey` を `autouse` で注入
- 追加:
```python
@pytest.fixture(autouse=True)
def patch_huey(monkeypatch):
    from tests.mocks.mock_huey import MockHuey
    import src.backend.tasks as t
    monkeypatch.setattr(t, 'huey', MockHuey())
```
- 期待: `test_background_worker.py` の import エラーが解消

**ステップ18**
- 対象: ターミナル
- コマンド: `python -m pytest tests/unit/test_background_worker.py -q`
- 期待: 収集エラーが出ない（中身は別途修正）

**ステップ19**
- 対象: `tests/mocks/mock_chroma.py`
- 作業: Chromadb `Client` の最小モックを作成
- 内容: `get_collection` が `AsyncMock` を返す
- 期待: import 可能

**ステップ20**
- 対象: `tests/conftest.py`
- 作業: `ChromaClientProvider` をモックに差し替え
- 追加: `monkeypatch.setattr('src.services.vector_store.ChromaClientProvider', MockChromaProvider)`
- 期待: `test_vector_store_lifecycle.py` の `assert _client is None` が通るようモックを整える

**ステップ21**
- 対象: ターミナル
- コマンド: `python -m pytest tests/unit/test_vector_store_lifecycle.py -q`
- 期待: 1件が pass する

**ステップ22**
- 対象: `tests/mocks/mock_llm_client.py`
- 作業: `MockGeminiApiClient.generate_json` を `AsyncMock` で応答できるように拡張
- 理由: `test_health.py` の LLM ゲートウェイ死活確認用
- 期待: `raise Exception` パスも再現可能

**ステップ23**
- 対象: `tests/conftest.py`
- 作業: `monkeypatch` で `core.llm_clients.gemini` のクライアントを差し替え
- 追加: `monkeypatch.setattr('src.core.llm_clients.gemini.GeminiClient', MockGeminiApiClient)`
- 期待: `test_health.py` の 2件が pass する見込み

**ステップ24**
- 対象: ターミナル
- コマンド: `python -m pytest tests/unit/test_health.py -q`
- 期待: 失敗が 0 または減少

**ステップ25**
- 対象: ターミナル
- コマンド: `python -m coverage run -m pytest -q > cov_run2.txt 2>&1; Select-String -Pattern "passed|failed" cov_run2.txt | Select-Object -Last 1`
- 期待: 失敗数が 82 から大幅減（例: 30 以下）

---

## 第2部: バックエンド中核のテスト補強（ステップ26〜40）

**ステップ26**
- 対象: `tests/unit/test_auth_service.py`
- 作業: `get_rate_limit_key` のハッシュ化検証を追加
- 追加: `sha256` 長さ 64 のアサーション
- 期待: 新テストが pass

**ステップ27**
- 対象: ターミナル
- コマンド: `python -m pytest tests/unit/test_auth_service.py -q`
- 期待: 5 passed

**ステップ28**
- 対象: `tests/unit/test_rate_limit_key.py`（新規）
- 作業: `RedisRateLimiter.is_allowed` がモック Redis で True/False を返すテスト
- 期待: モック `eval` の戻り値で分岐検証

**ステップ29**
- 対象: ターミナル
- コマンド: `python -m pytest tests/unit/test_rate_limit_key.py -q`
- 期待: pass

**ステップ30**
- 対象: `tests/unit/test_patch_validator_literal.py`（新規）
- 作業: 文字列リテラル内 `os.system` 検出テスト（L2）
- 期待: `is_safe=False` を確認

**ステップ31**
- 対象: ターミナル
- コマンド: `python -m pytest tests/unit/test_patch_validator_literal.py -q`
- 期待: pass

**ステップ32**
- 対象: `tests/unit/test_patch_validator.py`
- 作業: 既存テストが `DANGEROUS_FUNCTIONS` を拾うことを確認
- 期待: 失敗なら M2 の修正を見直す

**ステップ33**
- 対象: `src/backend/sse.py`
- 作業: `task_event_generator` の DB フォールバック経路のみをテスト対象に（Redis=None）
- 方針: `get_async_redis_client` を `None` を返すようモック
- 期待: SQLite ポーリング分岐が実行される

**ステップ34**
- 対象: `tests/unit/test_sse_fallback.py`（新規）
- 作業: `async for` でイベントが yield されることを検証
- 期待: 少なくとも 1 イベントを取得

**ステップ35**
- 対象: ターミナル
- コマンド: `python -m pytest tests/unit/test_sse_fallback.py -q`
- 期待: pass（sse.py カバレッジが 24% → 50% 程度に上昇）

**ステップ36**
- 対象: `src/backend/tasks.py`
- 作業: `_create_task` / `generate_task_id` の純関数部分を抽出
- 理由: 非同期 DB に依存しない部分を単体テストするため
- 期待: 関数シグネチャ変更なし

**ステップ37**
- 対象: `tests/unit/test_tasks_helpers.py`（新規）
- 作業: `generate_task_id` の形式検証
- 期待: プレフィックス付き ID が返る

**ステップ38**
- 対象: ターミナル
- コマンド: `python -m pytest tests/unit/test_tasks_helpers.py -q`
- 期待: pass（tasks.py カバレッジ向上）

**ステップ39**
- 対象: `src/backend/server.py`
- 作業: CORS 検証関数 `configure_cors` を独立させる（C2）
- 理由: 起動時失敗パスをテストしやすくする
- 期待: 既存呼び出しに影響なし

**ステップ40**
- 対象: `tests/unit/test_cors_config_unit.py`（新規）
- 作業: `allow_credentials=True & origins='*'` で例外になることを検証
- 期待: `pytest.raises` で pass

---

## 第3部: services / llm のテスト（ステップ41〜55）

**ステップ41**
- 対象: `tests/mocks/mock_llm_provider.py`
- 作業: `LLMProvider` 抽象クラスの最小実装モック
- 期待: import 可能

**ステップ42**
- 対象: `src/llm/model_router.py`
- 作業: `route()` の分岐（プロバイダ選択）を純関数化
- 理由: 0% の `model_router.py` をテスト可能に
- 期待: 既存 API はそのまま

**ステップ43**
- 対象: `tests/unit/test_model_router.py`（新規）
- 作業: キーに応じたプロバイダ選択を検証
- 期待: pass（model_router 0% → 70%）

**ステップ44**
- 対象: `src/llm/provider_factory.py`
- 作業: ファクトリの戻り値をモック可能に
- 期待: `monkeypatch` で差し替え可能

**ステップ45**
- 対象: `tests/unit/test_provider_factory.py`（新規）
- 作業: 未知キーでフォールバックすることを検証
- 期待: pass（provider_factory 0% → 60%）

**ステップ46**
- 対象: `src/llm/openai_provider.py`
- 作業: `generate()` の try/except 分岐を小さく切り出す
- 理由: 0% のままでは障害時挙動が未検証
- 期待: インタフェース維持

**ステップ47**
- 対象: `tests/unit/test_openai_provider.py`（新規）
- 作業: 例外時に `raise` するパスをモック LLM で検証
- 期待: pass（openai_provider 0% → 50%）

**ステップ48**
- 対象: `src/services/redis_cache.py`
- 作業: `RedisCacheService` の各メソッドが `self._client=None` で `False/None` を返すことを既存で確認
- 理由: 21% のままだが最低保証
- 期待: 変更なし

**ステップ49**
- 対象: `tests/unit/test_redis_cache_none.py`（新規）
- 作業: `client=None` の各メソッドで安全な戻り値を検証
- 期待: pass（redis_cache 向上）

**ステップ50**
- 対象: `src/services/writing_services.py`
- 作業: 外部 LLM 呼び出しを `inject` 可能な引数にする
- 理由: 16% のコアサービスをテスト可能に
- 期待: 既存呼び出し互換

**ステップ51**
- 対象: `tests/unit/test_writing_services.py`（新規）
- 作業: モック LLM で本文生成フローを検証
- 期待: pass（writing_services 向上）

**ステップ52**
- 対象: `src/services/semantic_cache.py`
- 作業: キャッシュヒット/ミス分岐を純関数化
- 期待: 変更最小

**ステップ53**
- 対象: `tests/unit/test_semantic_cache.py`（新規）
- 作業: ヒット率計算を検証
- 期待: pass

**ステップ54**
- 対象: `src/services/vector_store.py`
- 作業: `ChromaClientProvider` の `_client` 生成をモック化しやすく
- 期待: 変更最小

**ステップ55**
- 対象: ターミナル
- コマンド: `python -m coverage run -m pytest -q > cov_run3.txt 2>&1; Select-String -Pattern "passed|failed" cov_run3.txt | Select-Object -Last 1`
- 期待: 失敗数がさらに減り、カバレッジが 65% 程度に上昇

---

## 第4部: agents パッケージのテスト（ステップ56〜65）

**ステップ56**
- 対象: `tests/unit/test_agents_audit.py`（新規）
- 作業: `agents/audit.py` の純関数（スコア集計）を検証
- 期待: pass（audit 0% → 30%）

**ステップ57**
- 対象: `agents/writing/writing.py`
- 作業: `_build_*` ヘルパーを `PromptManager` 注入可能に
- 理由: 19% の巨大モジュールを分割テスト
- 期待: 既存ビルダー呼び出しは維持

**ステップ58**
- 対象: `tests/unit/test_writing_builders.py`（新規）
- 作業: 各 `_build_*` が期待文字列を返すことを検証
- 期待: pass（writing 向上）

**ステップ59**
- 対象: `agents/plot.py`
- 作業: プロット展開の純関数部分を抽出
- 期待: 変更最小

**ステップ60**
- 対象: `tests/unit/test_plot_agent.py`（新規）
- 作業: 展開ロジックをモック LLM で検証
- 期待: pass（plot 17% → 40%）

**ステップ61**
- 対象: `agents/context_builder.py`
- 作業: コンテキスト組み立ての単体ロジックを切り出し
- 期待: 9% → 30% 程度

**ステップ62**
- 対象: `tests/unit/test_context_builder.py`（新規）
- 作業: 辞書マージ結果を検証
- 期待: pass

**ステップ63**
- 対象: `agents/writing_scheduler.py`
- 作業: スケジュール計算の純関数を分離
- 期待: 11% → 30%

**ステップ64**
- 対象: `tests/unit/test_writing_scheduler.py`（新規）
- 作業: タイムテーブル生成を検証
- 期待: pass

**ステップ65**
- 対象: ターミナル
- コマンド: `python -m coverage run -m pytest -q > cov_run4.txt 2>&1; Select-String -Pattern "TOTAL" cov_full.txt` の代わりに `python -m coverage report --omit="..." | Select-String -Pattern "TOTAL"`
- 期待: カバレッジが 72% 程度に到達

---

## 第5部: フロントエンド / novel_50ep / 最終ゲート（ステップ66〜72）

**ステップ66**
- 対象: `frontend/`
- 作業: `package.json` に `vitest` と `test` スクリプトを追加
- 追加: `"test": "vitest run"` と devDependency
- 期待: `npm install` で vitest 導入

**ステップ67**
- 対象: `frontend/src/components/dialogs/SettingsModal.tsx`
- 作業: 最低限の `SettingsModal.test.tsx` を作成（render + ボタン存在）
- 期待: `npm test` で 1件 pass

**ステップ68**
- 対象: `pytest.ini`
- 作業: `testpaths` に `novel_50ep/tests` を追加（または別 workflow）
- 変更: `testpaths = tests novel_50ep/tests`
- 期待: novel_50ep の既存テストが収集される

**ステップ69**
- 対象: ターミナル
- コマンド: `python -m pytest novel_50ep/tests -q`
- 期待: novel_50ep のテストが pass（既存品質の確認）

**ステップ70**
- 対象: `pyproject.toml`
- 作業: `[tool.coverage.report] fail_under = 80` を追加
- 理由: CI で 80% 未満を強制失敗
- 期待: 設定が反映される

**ステップ71**
- 対象: `pytest.ini`
- 作業: `--cov` を戻す（本番CI用）
- 変更: `addopts = -v --tb=short --cov=src --cov=prompts --cov-report=term-missing`
- 期待: `pytest` 単体でカバレッジ付き実行

**ステップ72**
- 対象: ターミナル
- コマンド: `pytest -q` （または `python -m coverage run -m pytest -q`）
- 期待: **全体カバレッジ 80% 以上**、失敗 0 件、CI ゲート通過

---

## リスクと緩和

- **リスクA**: モック差し替えで本番挙動と乖離する。→ `autouse` フィクスチャは `tests/` 内のみ適用し、本番 import には影響しない。
- **リスクB**: `AppContainer.db` のモンキーパッチが効かない。→ ステップ13で `lambda` にするか `providers` の `override` を使う。
- **リスクC**: novel_50ep 追加で収集時間が長くなる。→ `pytest -m "not slow"` で並行。
- **リスクD**: フロントエンド導入で別言語カバレッジが混ざる。→ バックエンドは `coverage`、フロントは `vitest --coverage` で別計測。

## 完了条件

1. `pytest -q` が **0 failed**。
2. `coverage report` の **TOTAL ≥ 80%**。
3. `src/backend`（Critical/High 領域）が **90%** 以上。
4. `src/llm`, `src/agents` が **各 60%** 以上。
5. `frontend` に最低 1 テストが存在し、CI で実行される。
6. `novel_50ep/tests` が収集され、全件 pass。

---
*この計画は各ステップが独立しており、低性能LLMでも順次適用・検証可能。完了後に `IMPLEMENTATION_PLAN.md` の「Phase 0〜4」セクションに進捗を転記すること。*
