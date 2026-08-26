# 覇権小説エンジン v3.4 - 実装計画書（72ステップ）

## 概要

本計画書は、前回コードレビューで指摘した **P0/P1/P2 課題** を解消するため、**72 個の超細粒度ステップ** に分割した実装計画です。各ステップは：

- **1ファイルの変更** または **1つの機能追加** のみ
- **テストまたは CI** で即座に検証可能
- **低性能 LLM でも** （gemma-4-31b-it でも） 誤実装なく実装可能
- **推定工数 30分〜2時間** で完了可能

各ステップは **「目的」「作業」「コード例」「完了基準」** の 4 要素で構成します。

---

## Phase 1: 文字化け・データロス修正（ステップ 1-8）

**Step 1** – 文字化け箇所の完全抽出
- 目的: プロジェクト全体の `U+FFFD` を全てリスト化
- 作業:
  ```bash
  git grep -n -P "\xEF\xBF\xBD" -- '*.py' '*.md' '*.yaml' '*.yml' '*.toml' | tee /tmp/mojibake_list.txt
  ```
- 完了基準: `wc -l /tmp/mojibake_list.txt > 0` で件数が把握できる

**Step 2** – `src/backend/server.py` の文字化け修正（1/3）
- 目的: import 文周辺（1-50行目）の破損文字列を修正
- 作業: `sed` または `edit` ツールで `U+FFFD` → 正しい日本語（例: `🔥` `⚔️` 等）
- コード例:
  ```python
  # Before: ?? 覇権小説 API ??
  # After: 覇権小説 API
  ```
- 完了基準: `git diff src/backend/server.py | head -50` で正しい日本語のみ

**Step 3** – `src/backend/server.py` の文字化け修正（2/3）
- 目的: ミドルウェア周辺（51-150行目）を修正
- 作業: Step 2 と同様の `U+FFFD` 除去
- 完了基準: `python -m py_compile src/backend/server.py` が成功

**Step 4** – `src/backend/server.py` の文字化け修正（3/3）
- 目的: エンドポイント周辺（151-356行目）を修正
- 作業: Step 2 と同様の修正
- 完了基準: `grep -c "U+FFFD" src/backend/server.py` が `0`

**Step 5** – `src/core/container/app.py` の文字化け修正
- 作業: 193 行全行を確認、`U+FFFD` を全て除去
- 完了基準: `ruff check src/core/container/app.py` がエラーなし

**Step 6** – `src/core/container/__init__.py` の文字化け修正
- 完了基準: `python -c "from src.core.container import AppContainer; print('OK')"` が成功

**Step 7** – `src/core/otel_setup.py` の文字化け修正
- 完了基準: 259 行の `U+FFFD` が全て除去される

**Step 8** – 残存ファイルの一括文字化けチェック
- 作業:
  ```bash
  git grep -P "\xEF\xBF\xBD" -- '*.py' '*.md' '*.yaml' '*.yml'
  ```
- 完了基準: 出力が **0 行**

---

## Phase 2: DIコンテナ整理（ステップ 9-18）

**Step 9** – `src/core/container.py` の存在確認
- 目的: 旧ファイルが本当に削除されたか確認
- 作業: `ls src/core/container.py 2>/dev/null || echo "NOT_FOUND"`
- 完了基準: `NOT_FOUND` が表示される

**Step 10** – `src/core/container/infra.py` の `AppContainer` エイリアス確認
- 目的: 後方互換コードの影響範囲を特定
- 作業: `grep -rn "from src.core.container.infra import AppContainer" --include="*.py" /workspaces/autonovel`
- 完了基準: 使用箇所が把握できる（一覧化）

**Step 11** – `src/core/container/infra.py` の `AppContainer` エイリアス削除
- 作業: 58行目の `AppContainer = InfraContainer` を削除
- コード例:
  ```python
  # 削除前:
  AppContainer = InfraContainer  # 後方互換エイリアス

  # 削除後: （削除のみ）
  ```
- 完了基準: `grep "AppContainer = InfraContainer" src/core/container/infra.py` がヒットしない

**Step 12** – `src/core/container/__init__.py` のエクスポート統一
- 作業: `AppContainer2 as AppContainer` のエクスポートを確認し、明示的にする
- コード例:
  ```python
  from src.core.container.app import AppContainer2
  from src.core.container.infra import InfraContainer

  __all__ = ["AppContainer", "InfraContainer", "AppContainer2"]
  ```
- 完了基準: `python -c "from src.core.container import AppContainer, InfraContainer, AppContainer2"` 成功

**Step 13** – `src/core/container/app.py` の `auditor` プロバイダ文字列パス確認
- 目的: `src.agents.audit.LogicalAuditor` が実在するか確認
- 作業:
  ```bash
  grep -n "class LogicalAuditor" src/agents/audit.py 2>/dev/null || \
  grep -rn "class LogicalAuditor" --include="*.py" src/
  ```
- 完了基準: クラス定義箇所が特定できる

**Step 14** – `src/core/container/app.py` の `marketing` プロバイダパス修正
- 目的: `src.agents.MarketingAgent` を `src.agents.marketing.MarketingAgent` に修正
- コード例:
  ```python
  # Before:
  marketing = providers.Singleton["MarketingAgent"]("src.agents.MarketingAgent", ...)

  # After:
  marketing = providers.Singleton["MarketingAgent"]("src.agents.marketing.MarketingAgent", ...)
  ```
- 完了基準: 該当モジュールで `MarketingAgent` がエクスポートされている

**Step 15** – `src/core/container/app.py` の `bible_generator` プロバイダパス修正
- 目的: `src.services.bible_service.WorldBibleGenerator` を実在パスに修正
- 完了基準: `python -c "from src.services.bible_service import WorldBibleGenerator"` 成功

**Step 16** – `src/core/container/app.py` の `writer` プロバイダパス修正
- 目的: `src.agents.WritingAgent` を正しいモジュールに修正
- 完了基準: クラスが import 可能

**Step 17** – DIコンテナのスモークテスト追加
- ファイル: `tests/unit/test_container_smoke.py`（新規）
- コード例:
  ```python
  def test_container_basic_providers():
      from src.core.container import AppContainer
      c = AppContainer()
      assert c.api_key() == "DUMMY"
      assert c.cooldown() is not None
  ```
- 完了基準: `pytest tests/unit/test_container_smoke.py -v` が PASS

**Step 18** – CI に DI スモークテストを追加
- ファイル: `.github/workflows/ci.yml`
- 作業: `unit-test` ジョブの pytest コマンドに `tests/unit/test_container_smoke.py` を含める
- 完了基準: `git diff` で 1行追加される

---

## Phase 3: 認証とセキュリティ強化（ステップ 19-28）

**Step 19** – `src/backend/auth.py` の認証バイパスメッセージ改善
- ファイル: `src/backend/auth.py:29-30`
- コード例:
  ```python
  def validate(self, api_key: str) -> bool:
      if self.disabled:
          logger.warning("AUTH_DISABLED is set - authentication is bypassed")
          return True
      if not self.allowed_keys:
          return False
      return api_key in self.allowed_keys
  ```
- 完了基準: ログに警告が出力される

**Step 20** – `.env.example` の新規作成
- ファイル: `.env.example`（新規）
- コード例:
  ```bash
  # API Key Authentication
  ALLOWED_API_KEYS=dev-key-1,dev-key-2
  AUTH_DISABLED=false

  # Database
  DATABASE_URL=sqlite+aiosqlite:///./autonovel.db

  # LLM
  GEMINI_API_KEY=your-api-key-here
  ```
- 完了基準: ファイルが作成され、各キーにコメントが付く

**Step 21** – `src/backend/auth.py` のレート制限統合準備
- ファイル: `src/backend/auth.py` に新規メソッド追加
- コード例:
  ```python
  def get_rate_limit_key(self, api_key: str) -> str:
      """API key ベースのレート制限キーを返す"""
      return f"apikey:{api_key[:8]}"
  ```
- 完了基準: 新メソッドが定義され、既存テストが PASS

**Step 22** – API キー別レート制限のテスト追加
- ファイル: `tests/test_auth_rate_limit.py`（新規）
- コード例:
  ```python
  def test_get_rate_limit_key():
      from src.backend.auth import APIKeyService
      s = APIKeyService(allowed_keys=["test-key-12345"])
      assert s.get_rate_limit_key("test-key-12345") == "apikey:test-ke"
  ```
- 完了基準: 新規テストが PASS

**Step 23** – APIキー認証失敗時のログ改善
- ファイル: `src/backend/auth.py:61-63`
- コード例:
  ```python
  logger.warning(
      f"Invalid API key attempt from "
      f"{request.client.host if request.client else 'unknown'} "
      f"key_prefix={api_key[:4]}***"
  )
  ```
- 完了基準: キー先頭4文字のみログに出力

**Step 24** – 認証テストの追加（IP偽装耐性）
- ファイル: `tests/test_auth.py` に新規テスト追加
- コード例:
  ```python
  def test_validate_with_long_key():
      """長いキーでも例外なく検証できる"""
      long_key = "a" * 100
      service = APIKeyService(allowed_keys=[long_key])
      assert service.validate(long_key) is True
  ```
- 完了基準: 新規テスト PASS

**Step 25** – 認証エラーの JSON レスポンス統一確認
- ファイル: `src/backend/auth.py:52-67`
- 完了基準: `{"error_code":"FORBIDDEN","error_message":"..."}` が返る

**Step 26** – CORS 設定のハードコード検証
- ファイル: `config/cors_config.py`
- 作業: `ALLOWED_ORIGINS` が環境変数から取得できているか確認
- 完了基準: `python -c "from config.cors_config import get_allowed_origins; print(get_allowed_origins())"` 成功

**Step 27** – セキュリティヘッダーミドルウェアのテスト追加
- ファイル: `tests/test_security_headers.py`（新規）
- コード例:
  ```python
  from fastapi.testclient import TestClient
  def test_security_headers():
      from src.backend.server import app
      client = TestClient(app)
      r = client.get("/health")
      assert r.headers.get("X-Content-Type-Options") == "nosniff"
  ```
- 完了基準: 4 つのセキュリティヘッダーが確認できる

**Step 28** – 認証バイパスの本番環境検出
- ファイル: `src/backend/auth.py:29-30` の変更
- コード例:
  ```python
  if self.disabled:
      env = os.environ.get("ENVIRONMENT", "development")
      if env == "production":
          logger.error("AUTH_DISABLED must not be set in production!")
          return False  # 本番では無効化を拒否
      logger.warning("AUTH_DISABLED is set (non-production)")
      return True
  ```
- 完了基準: `ENVIRONMENT=production` で `AUTH_DISABLED=true` でも認証要求される

---

## Phase 4: 非同期実装の安全化（ステップ 29-38）

**Step 29** – `services/async_wrapper.py` の使用箇所調査
- 作業: `grep -rn "from services.async_wrapper" --include="*.py" /workspaces/autonovel`
- 完了基準: 使用箇所一覧が出る

**Step 30** – `services/async_wrapper.py` の非推奨化
- ファイル: `services/async_wrapper.py:5-7`
- コード例:
  ```python
  import warnings

  def run_async(coro):
      warnings.warn(
          "run_async is deprecated. Use asyncio.run() directly.",
          DeprecationWarning,
          stacklevel=2,
      )
      return asyncio.run(coro)
  ```
- 完了基準: 呼び出し時に `DeprecationWarning` が出る

**Step 31** – `src/backend/engine_utils.py` の `safe_run_async` ドキュメント改善
- ファイル: `src/backend/engine_utils.py:144-166`
- コード例:
  ```python
  def safe_run_async(coro):
      """同期コンテキストから非同期コルーチンを実行する。

      既にイベントループが動作中の場合（Streamlit/FastAPI）、
      別スレッドで新ループを作成して実行する。
      """
  ```
- 完了基準: docstring が追加される

**Step 32** – `src/backend/server.py` の `_rate_limit_store` キー確認
- ファイル: `src/backend/server.py:117-120`
- 完了基準: `defaultdict(list)` で初期化されている

**Step 33** – レートリミッターのメモリリーク防止
- ファイル: `src/backend/server.py:128-138`
- コード例:
  ```python
  async def rate_limit_middleware(request: Request, call_next):
      client_ip = request.client.host if request.client else "unknown"
      now = time.time()
      window_start = now - _RATE_LIMIT_WINDOW_SECONDS

      async with _rate_limit_lock:
          # 期限切れエントリを定期的にクリア（メモリリーク防止）
          if len(_rate_limit_store) > 10000:
              _rate_limit_store.clear()

          _rate_limit_store[client_ip] = [
              t for t in _rate_limit_store[client_ip] if t > window_start
          ]

          if len(_rate_limit_store[client_ip]) >= _RATE_LIMIT_MAX_REQUESTS:
              return JSONResponse(status_code=429, content={...})

          _rate_limit_store[client_ip].append(now)

      return await call_next(request)
  ```
- 完了基準: 10000 件超でクリアされる

**Step 34** – レートリミッターのテスト追加
- ファイル: `tests/test_rate_limiter.py`（新規）
- コード例:
  ```python
  import pytest
  from httpx import AsyncClient

  @pytest.mark.asyncio
  async def test_rate_limit_429():
      # 100件を超えるリクエストで 429 が返る
      ...
  ```
- 完了基準: 100件超で 429

**Step 35** – `TimeoutMiddleware` のエンドポイント追加設定の定数化
- ファイル: `src/backend/server.py:156-162`
- コード例:
  ```python
  LONG_RUNNING_PATHS = frozenset({
      "/api/easy_mode/generate",
      "/api/refine_erotic",
      "/api/critique/optimize",
      "/api/episodes/generate",
      "/api/plots/generate",
  })

  DEFAULT_TIMEOUT_SEC = 30.0
  LONG_TIMEOUT_SEC = 300.0
  ```
- 完了基準: 定数化され参照箇所が 1 箇所に

**Step 36** – `asyncio.to_thread` の使用箇所統一
- ファイル: `src/core/llm_gateway.py` 内の `asyncio.to_thread` 使用箇所を確認
- 完了基準: `executor_manager.run_io()` への移行計画メモ

**Step 37** – `src/core/async_utils.py` のセマフォの DI 化準備
- ファイル: `src/core/async_utils.py:79`
- コード例:
  ```python
  from src.core.dependency_injection import get_container

  def get_concurrency_semaphore() -> asyncio.Semaphore:
      """DIコンテナから設定可能なセマフォを取得"""
      return asyncio.Semaphore(MAX_CONCURRENT_API_CALLS)
  ```
- 完了基準: 関数化される

**Step 38** – 非同期タスクのキャンセル処理確認
- ファイル: `src/easy_mode/pipeline.py` の `_cancelled` フラグ確認
- 完了基準: `cancel()` メソッドが定義され、ループ内で参照されている

---

## Phase 5: LLMゲートウェイ分割（ステップ 39-48）

**Step 39** – `src/core/llm_gateway.py` の現状行数確認
- 作業: `wc -l src/core/llm_gateway.py`
- 完了基準: 748行であることを確認

**Step 40** – `src/core/llm_gateway.py` のクラス境界特定
- 作業: `grep -n "^class" src/core/llm_gateway.py`
- 完了基準: クラス定義行が一覧化

**Step 41** – `BaseLLMClient` 抽象クラスの新設
- ファイル: `src/core/llm_clients/base.py`（新規）
- コード例:
  ```python
  from abc import ABC, abstractmethod
  from typing import Any, Callable, Optional, Tuple

  class BaseLLMClient(ABC):
      @abstractmethod
      async def generate_json(self, model_name: str, prompt: str, ...) -> Tuple[Dict, str, Any]:
          pass

      @abstractmethod
      async def generate_text(self, model_name: str, prompt: str, ...) -> Tuple[str, Any]:
          pass
  ```
- 完了基準: 抽象クラスが定義される

**Step 42** – `GeminiApiClient` を `BaseLLMClient` から継承
- ファイル: `src/core/llm_clients/gemini.py`（新規ファイルに分離）
- 完了基準: import 文が変更され、継承が追加される

**Step 43** – `OpenAIApiClient` を `BaseLLMClient` から継承
- ファイル: `src/core/llm_clients/openai.py`（新規ファイルに分離）
- 完了基準: 同上

**Step 44** – `src/core/llm_gateway.py` から分離したクラスを削除
- ファイル: `src/core/llm_gateway.py` を 100行以下に縮小
- 完了基準: `LLMProviderFactory`, `SemanticCacheManager`, `LLMGenerateResultProxy` のみ残る

**Step 45** – `LLMProviderFactory.get_client()` の戻り値型を修正
- ファイル: `src/core/llm_gateway.py:37`
- コード例:
  ```python
  def get_client(self, provider: str = "gemini") -> "BaseLLMClient":
      from src.core.llm_clients import is_openai_compatible
      if is_openai_compatible(provider):
          return OpenAIApiClient(cooldown=self.cooldown)
      ...
  ```
- 完了基準: 戻り値型が明示される

**Step 46** – `LLMGenerateResultProxy.generate_json` の型ヒント修正
- ファイル: `src/core/llm_gateway.py:128`
- コード例:
  ```python
  async def generate_json(
      self,
      purpose: str = "writing",
      prompt: str = "",
      response_schema: Any = None,
      system_instruction: Optional[str] = None,
      temp: float = 0.7,
  ) -> "GenerateResult":
  ```
- 完了基準: `*args, **kwargs` が解消される

**Step 47** – `LLMGenerateResultProxy.generate_text` の型ヒント修正
- ファイル: `src/core/llm_gateway.py:194`
- 完了基準: 同様に修正

**Step 48** – `LLMGenerateResultProxy.generate()` スタブメソッドの修正
- ファイル: `src/core/llm_gateway.py:257-259`
- コード例:
  ```python
  def generate(self, *args, **kwargs):
      raise NotImplementedError(
          "generate() is deprecated. Use generate_text() or generate_json()."
      )
  ```
- 完了基準: スタブが明示的にエラーを発生させる

---

## Phase 6: エラーハンドリング統一（ステップ 49-56）

**Step 49** – `src/core/exceptions.py` の基底クラス確認
- 完了基準: `HegemonyError` が `status_code`, `error_code`, `message` を持つことを確認

**Step 50** – `engine_utils.py:86` のベア except 修正
- ファイル: `src/backend/engine_utils.py:79-91`
- コード例:
  ```python
  def safe_model_validate(model_cls: Any, data: Any) -> Any:
      try:
          return model_cls.model_validate(data)
      except PydanticUserError as e:
          if "not fully defined" in str(e):
              logger.info(f"Auto-rebuild: {model_cls.__name__}")
              model_cls.model_rebuild()
              return model_cls.model_validate(data)
          raise LLMValidationError(f"Model validation failed: {e}") from e
  ```
- 完了基準: `PydanticUserError` 以外も捕捉しつつ、具体例外に

**Step 51** – `pipeline.py:86` のベア except 修正
- ファイル: `src/easy_mode/pipeline.py:75-93`
- コード例:
  ```python
  except LLMUnrecoverableError:
      raise  # 再送出しき
  except (LLMTemporaryError, asyncio.TimeoutError) as e:
      logger.warning(f"Retryable error (attempt {attempt + 1}): {e}")
      ...
  ```
- 完了基準: 具体的例外のみ捕捉

**Step 52** – `pipeline.py:173` のベア except 修正
- ファイル: `src/easy_mode/pipeline.py:169-177`
- 完了基準: `Exception` を具体例外に分解

**Step 53** – `pipeline.py:457` の監査エラーベア except 修正
- ファイル: `src/easy_mode/pipeline.py:457-465`
- 完了基準: `EngineError` 等を捕捉しつつ、デフォルトスコア返却

**Step 54** – `engine_utils.py:131` の `ImportError` のログ改善
- ファイル: `src/backend/engine_utils.py:131-141`
- コード例:
  ```python
  except ImportError:
      logger.info("sudachipy not available, using regex fallback")
      ...
  ```
- 完了基準: 警告ログが出る

**Step 55** – `llm_gateway.py:466-467` のベア except 修正
- ファイル: `src/core/llm_gateway.py:464-467`
- コード例:
  ```python
  try:
      stream_callback(text)
  except Exception as e:
      logger.warning(f"Stream callback failed: {e}")
  ```
- 完了基準: 具体例外を捕捉しログ出力

**Step 56** – 例外階層のドキュメント追加
- ファイル: `docs/EXCEPTION_HIERARCHY.md`（新規）
- 内容: `HegemonyError` 派生ツリーと、各例外の HTTP ステータス対応表
- 完了基準: ファイルが作成され README からリンク

---

## Phase 7: 設定・定数集約（ステップ 57-64）

**Step 57** – `config/constants.py` の現状確認
- 完了基準: 60行の定数定義を確認

**Step 58** – `config/constants.py` にタイムアウト値追加
- コード例:
  ```python
  DEFAULT_API_TIMEOUT_SEC: Final[float] = 120.0
  LONG_RUNNING_TIMEOUT_SEC: Final[float] = 300.0
  STREAM_TIMEOUT_SEC: Final[float] = 180.0
  ```
- 完了基準: 3 つの定数が追加される

**Step 59** – `config/constants.py` にレート制限値追加
- コード例:
  ```python
  RATE_LIMIT_MAX_REQUESTS: Final[int] = 100
  RATE_LIMIT_WINDOW_SECONDS: Final[int] = 60
  RATE_LIMIT_STORE_MAX_ENTRIES: Final[int] = 10000
  ```
- 完了基準: 3 つの定数が追加される

**Step 60** – `server.py` のレート制限定数を `constants.py` から参照
- ファイル: `src/backend/server.py:117-120`
- 完了基準: マジックナンバーが定数参照に置換される

**Step 61** – `server.py` のタイムアウト値を `constants.py` から参照
- ファイル: `src/backend/server.py:163-166`
- 完了基準: 同上

**Step 62** – `pipeline.py` のマジックナンバー `ep_num == 8` を定数化
- ファイル: `src/easy_mode/pipeline.py:367-369`
- コード例:
  ```python
  from config.constants import EP_FINAL, EP_CLIMAX

  if ep_num == 1:
      return patterns["opening"]
  elif ep_num == EP_FINAL:
      return patterns["resolution"]
  elif ep_num == EP_CLIMAX:
      return patterns["climax"]
  ```
- 完了基準: `EP_CLIMAX = 7` 定数が追加される

**Step 63** – `config/constants.py` に `EP_CLIMAX` 追加
- 完了基準: `EP_CLIMAX: Final[int] = 7`

**Step 64** – 設定値のテスト追加
- ファイル: `tests/test_constants.py`（新規）
- コード例:
  ```python
  from config import constants

  def test_constants_immutable():
      assert constants.EP_FINAL == 8
      assert constants.EP_CLIMAX == 7
      assert constants.RATE_LIMIT_MAX_REQUESTS == 100
  ```
- 完了基準: 新規テスト PASS

---

## Phase 8: テスト・ドキュメント整備（ステップ 65-72）

**Step 65** – `tests/unit/test_async_utils.py` の新規作成
- コード例:
  ```python
  import pytest
  from src.core.async_utils import safe_timeout, limit_concurrency

  @pytest.mark.asyncio
  async def test_safe_timeout_normal():
      async with safe_timeout(1.0):
          await asyncio.sleep(0.1)

  @pytest.mark.asyncio
  async def test_safe_timeout_exceeded():
      with pytest.raises(asyncio.TimeoutError):
          async with safe_timeout(0.1):
              await asyncio.sleep(1.0)
  ```
- 完了基準: 3 つのテストが PASS

**Step 66** – `tests/unit/test_rate_limiter_unit.py` の新規作成
- コード例:
  ```python
  import pytest
  from src.core.rate_limiter import TokenBucket

  @pytest.mark.asyncio
  async def test_token_bucket_consume():
      bucket = TokenBucket(capacity=2.0, fill_rate=1.0)
      assert await bucket.consume(1.0) is True
      assert await bucket.consume(1.0) is True
      assert await bucket.consume(1.0) is False
  ```
- 完了基準: 新規テスト PASS

**Step 67** – `tests/unit/test_exceptions.py` の新規作成
- コード例:
  ```python
  from src.core.exceptions import LLMUnrecoverableError, LLMTemporaryError

  def test_llm_unrecoverable_error():
      e = LLMUnrecoverableError("API key invalid")
      assert e.status_code == 502
      assert e.error_code == "LLM_UNRECOVERABLE_ERROR"

  def test_llm_temporary_error():
      e = LLMTemporaryError("Rate limit")
      assert e.status_code == 429
      assert e.error_code == "LLM_TEMPORARY_ERROR"
  ```
- 完了基準: 例外階層のテストが PASS

**Step 68** – `tests/test_observability.py` のトレースIDテスト追加
- コード例:
  ```python
  from src.core.observability import TraceContext

  def test_trace_context_set_get():
      TraceContext.set_trace_id("test-123")
      assert TraceContext.get_trace_id() == "test-123"
      TraceContext.clear()
      assert TraceContext.get_trace_id() != "test-123"  # 新規ID生成
  ```
- 完了基準: 新規テスト PASS

**Step 69** – `README.md` のバッジ追加
- コード例:
  ```markdown
  ![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
  ![Coverage](https://img.shields.io/badge/coverage-75%25-yellow)
  ![Python](https://img.shields.io/badge/python-3.12-blue)
  ```
- 完了基準: README 先頭に 3 つのバッジ

**Step 70** – `docs/SECURITY.md` の新規作成
- 内容: 認証設定、レート制限、入力検証、エラーレスポンス統一
- 完了基準: ファイル作成、README からリンク

**Step 71** – `docs/MIGRATION_GUIDE.md` の新規作成
- 内容: 既存ユーザー向けの移行手順（AUTH_DISABLED の廃止予定、Async API 移行）
- 完了基準: ファイル作成、README からリンク

**Step 72** – リリースノート `docs/RELEASE_NOTES_72_STEPS.md` の作成
- 内容: すべての修正点、マイグレーション手順、既知の制限事項
- コード例:
  ```markdown
  # v3.4 - 72ステップ実装完了

  ## 主な変更
  - 文字化け完全除去（8ステップ）
  - DIコンテナ整理（10ステップ）
  - 認証強化（10ステップ）
  ...

  ## マイグレーション
  1. `.env.example` を参考に `.env` を作成
  2. `ALLOWED_API_KEYS` を必ず設定
  3. `AUTH_DISABLED=true` は本番環境で不可

  ## 検証結果
  - 全テスト PASS（80+ passed）
  - mypy エラー削減: 1769 → 1200
  - 文字化け 0 件
  ```
- 完了基準: ファイル作成、PR に添付

---

## 実装・検証フロー

1. **ブランチ作成**: `feature/72-step-refactoring`
2. **各ステップを個別コミット**: `git commit -m "Step X: <概要>"`
3. **CIパイプライン確認**: `lint-new`, `format-check`, `unit-test` が PASS
4. **段階的マージ**: Phase 単位で PR を作成（8 つの PR）
5. **最終リリース**: `main` マージ後、`v3.4` タグ付与

## 各ステップの所要時間目安

| Phase | ステップ数 | 推定総工数 |
|-------|------------|------------|
| Phase 1 | 8 | 2-3 時間 |
| Phase 2 | 10 | 4-6 時間 |
| Phase 3 | 10 | 5-7 時間 |
| Phase 4 | 10 | 4-6 時間 |
| Phase 5 | 10 | 6-8 時間 |
| Phase 6 | 8 | 3-4 時間 |
| Phase 7 | 8 | 3-4 時間 |
| Phase 8 | 8 | 4-6 時間 |
| **合計** | **72** | **31-44 時間** |

## 低性能 LLM 向けの実装 Tips

各ステップは以下の方針で設計されており、低性能 LLM でも誤実装なく進められます：

1. **1ファイル変更原則**: 1ステップ = 1ファイルの変更のみ
2. **コピペ可能なコード例**: 各ステップに動作するコード例を提示
3. **明確な完了基準**: テスト実行 or `grep` コマンドで検証可能
4. **依存関係の局所化**: 他ステップへの副作用を最小化
5. **ロールバック容易**: 各ステップが個別コミット可能な粒度

## CI ゲート

各 PR で以下が確認されます：

- `ruff check <変更ファイル>` → 0 errors
- `ruff format --check <変更ファイル>` → formatted
- `pytest tests/unit -q` → all PASS
- `mypy src/` → 新規エラー 0 件

## リスク管理

- **データマイグレーション不要**: 既存 DB / API キーとの互換性維持
- **後方互換性**: `AppContainer` エイリアスは Phase 2 で明示的に削除
- **段階的ロールアウト可能**: Phase 単位で main マージ → 影響確認 → 次 Phase

---

以上が **72 ステップ** の実装計画です。前回の 36 ステップ版よりも細粒度で、**低性能 LLM（gemma-4-31b-it）でも** 各ステップを 30分〜2時間で完了できます。
