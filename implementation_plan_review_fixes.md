# コードレビュー指摘事項 実装計画書

## 概要

前回のコードレビューで残存が確認された 9 件の課題を解消するための実装計画。
各ステップは 1 ファイル・1 PR レベルで完結し、低性能 LLM でも機械的に実装可能な粒度に分割している。

## 対象課題一覧

| ID | 重大度 | 課題 | 対象ファイル |
|----|--------|------|-------------|
| F-01 | 高 | `invalidate_task_type` のパターン不一致 | `src/services/redis_cache.py` |
| F-02 | 高 | Redis 例外クラスの import 漏れ可能性 | `src/services/redis_cache.py` |
| F-03 | 中 | UUID 12 文字切り詰めによる衝突リスク | `src/backend/utils/id_generator.py` |
| F-04 | 中 | `except Exception` の狭化と `trace_id` 付与 | `src/backend/tasks.py`, `src/backend/workflows/writing_langgraph.py`, `src/backend/database/core.py` |
| F-05 | 中 | 本番コードの `print` 文残存 | `src/backend/kakuyomu/commercial_validation.py`, `src/cli/promptops.py` |
| F-06 | 中 | `redis_util.py` のグローバル可変状態 | `src/backend/redis_util.py` |
| F-07 | 中 | `safe_run_async` の ThreadPoolExecutor 生成コスト | `src/backend/engine_utils.py` |
| F-08 | 低 | `run_validation` の asyncio.run 混在 | `src/backend/kakuyomu/commercial_validation.py` |
| F-09 | 低 | `archive/` ディレクトリの Git 追跡 | プロジェクトルート |

## 実装ステップ（1〜36）

各ステップには「変更ファイル」「具体的な差分」「検証コマンド」を明示する。

---

### ステップ 1: 現状のベースラインを記録する
- **目的**: 修正前の品質指標を固定する
- **作業**:
  1. `mypy --strict src 2>&1 | tee /tmp/mypy_before.txt` を実行し、エラー数を記録
  2. `ruff check src 2>&1 | tee /tmp/ruff_before.txt` を実行し、違反数を記録
  3. `pytest tests/ --co -q 2>&1 | tee /tmp/pytest_collect_before.txt` でテスト収集数を記録
  4. 記録内容を `coverage_review.md` の末尾に追記
- **検証**: 3 つのテキストファイルが生成されること
- **コミット**: なし（記録のみ）

---

### ステップ 2: 作業ブランチを作成する
- **作業**:
  1. `git checkout -b refactor/code-review-fixes`
  2. `git status` でクリーン状態を確認
- **検証**: ブランチが切り替わっていること

---

### ステップ 3: F-01 のテストを先に追加する（TDD）
- **対象**: `tests/services/test_redis_cache_invalidate.py`（新規）
- **作業**: 以下のテストを書く
  ```python
  import pytest
  from src.services.redis_cache import PromptCacheService
  from unittest.mock import AsyncMock

  @pytest.mark.asyncio
  async def test_invalidate_task_type_pattern_matches_real_key():
      # 実キー: prompt:tpl:model:1.0:generation:abcdef0123456789
      redis = AsyncMock()
      redis.invalidate_pattern = AsyncMock(return_value=5)
      svc = PromptCacheService(redis_cache=redis)

      # パターン呼び出しを捕捉
      captured = {}
      async def capture(pattern):
          captured["pattern"] = pattern
          return 5
      redis.invalidate_pattern = capture

      result = await svc.invalidate_task_type("generation")
      assert result == 5
      # 期待パターン: prompt:*:*:*:generation:* （6要素のうち task_type は 5 番目）
      assert captured["pattern"] == "prompt:*:*:*:generation:*"
      # 現在のバグ実装: "prompt:*:*:*:*:generation:*" なので 7 セクションになり不一致
  ```
- **検証**: `pytest tests/services/test_redis_cache_invalidate.py -v` で **失敗** することを確認

---

### ステップ 4: F-01 を修正する
- **対象**: `src/services/redis_cache.py:625`
- **変更前**:
  ```python
  pattern = f"prompt:*:*:*:*:{task_type}:*"
  ```
- **変更後**:
  ```python
  pattern = f"prompt:*:*:*:{task_type}:*"
  ```
- **検証**: ステップ 3 のテストがパスすること

---

### ステップ 5: F-01 の追加テスト（テンプレート別と書籍別）を確認する
- **対象**: `src/services/redis_cache.py:602-620`
- **作業**:
  - `invalidate_template` のパターン `prompt:{template_name}:*` は正しい
  - `invalidate_book` のパターン `*:book:{book_id}:*` は実キーに `book_id` が含まれないため**バグ**だが、別タスクとして記録
- **検証**: コメントのみ追加（修正はしない）
  ```python
  # NOTE: invalidate_book は実キーに book_id を含まないため未実装。
  # 将来 book_id をキー構造に含めるか、別インデックスを併用する。
  ```

---

### ステップ 6: F-02 の import 状況を確認する
- **対象**: `src/services/redis_cache.py`（先頭 import ブロック）
- **作業**:
  1. ファイル冒頭の import を `grep -n "Redis" src/services/redis_cache.py | head -20` で確認
  2. `RedisConnectionError`, `RedisTimeoutError`, `RedisError` が import されているか検証
- **想定される正しい import**:
  ```python
  from redis.exceptions import (
      ConnectionError as RedisConnectionError,
      TimeoutError as RedisTimeoutError,
      RedisError,
  )
  ```

---

### ステップ 7: F-02 の import を修正する
- **対象**: `src/services/redis_cache.py`（import ブロック）
- **作業**: ステップ 6 で不足している import を追加
- **検証**: `python -c "from src.services.redis_cache import PromptCacheService"` が `NameError` なく成功すること

---

### ステップ 8: F-02 の動作テストを追加する
- **対象**: `tests/services/test_redis_cache_imports.py`（新規）
- **作業**:
  ```python
  def test_redis_exceptions_imported():
      from src.services.redis_cache import (
          RedisConnectionError,
          RedisTimeoutError,
          RedisError,
      )
      assert RedisConnectionError is not None
  ```
- **検証**: `pytest tests/services/test_redis_cache_imports.py -v` がパス

---

### ステップ 9: F-03 のテストを追加する
- **対象**: `tests/backend/test_id_generator.py`（新規）
- **作業**:
  ```python
  import re
  from src.backend.utils.id_generator import generate_prefixed_id


  def test_default_length_is_at_least_16():
      """UUID 切り詰め長 >= 16 で衝突確率を下げる"""
      tid = generate_prefixed_id("test")
      suffix = tid.split("_", 1)[1]
      assert len(suffix) >= 16


  def test_explicit_length_works():
      tid = generate_prefixed_id("t", length=20)
      assert len(tid.split("_", 1)[1]) == 20
  ```
- **検証**: `pytest tests/backend/test_id_generator.py -v` で **失敗** することを確認（現在 12 文字）

---

### ステップ 10: F-03 を修正する
- **対象**: `src/backend/utils/id_generator.py`
- **変更前**:
  ```python
  def generate_prefixed_id(prefix: str, length: int = 12) -> str:
      return f"{prefix}_{uuid.uuid4().hex[:length]}"
  ```
- **変更後**:
  ```python
  def generate_prefixed_id(prefix: str, length: int = 16) -> str:
      """プレフィックス付きの一意IDを生成

      デフォルト 16 文字 (64bit) は UUIDv4 空間から生成され、
      100万件生成時の衝突確率は約 2.7e-8 (birthday paradox)。
      """
      return f"{prefix}_{uuid.uuid4().hex[:length]}"
  ```
- **検証**: ステップ 9 のテストがパス

---

### ステップ 11: F-03 の呼び出し側を検証する
- **対象**: すべての `generate_task_id` 呼び出し
- **作業**:
  1. `grep -rn "generate_task_id" src/ tests/ | grep -v ".pyc"` を実行
  2. すべての呼び出しが `prefix` のみを渡しており、デフォルト長変更の影響を受けないことを確認
  3. 例: `routers/narrative.py:75 task_id = generate_task_id("override_affinity")` → 自動的に 16 文字になる
- **検証**: `grep` の結果に `length=` 指定がないこと

---

### ステップ 12: F-04 のトレースコンテキストモジュールを確認する
- **対象**: `src/core/observability.py` の `TraceContext`
- **作業**:
  1. `grep -n "class TraceContext\|def get_trace_id" src/core/observability.py` で存在確認
  2. 存在しない場合は次のようなヘルパーを新規作成:
     ```python
     # src/core/observability.py に追加
     import contextvars
     _trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
         "trace_id", default=None
     )

     class TraceContext:
         @staticmethod
         def set(trace_id: str) -> None:
             _trace_id_var.set(trace_id)

         @staticmethod
         def get_trace_id() -> str | None:
             return _trace_id_var.get()
     ```
- **検証**: `python -c "from src.core.observability import TraceContext; print(TraceContext.get_trace_id())"` が `None` を返す

---

### ステップ 13: F-04 の共通エラーハンドラユーティリティを作成する
- **対象**: `src/backend/error_utils.py`（既に存在するか確認）
- **作業**:
  1. `cat src/backend/error_utils.py | head -50` で確認
  2. 無ければ新規作成:
     ```python
     """例外処理とログ出力の共通ユーティリティ"""
     from __future__ import annotations
     import logging
     from typing import TypeVar
     from src.core.observability import TraceContext

     T = TypeVar("T")

     def log_exception(
         logger: logging.Logger,
         msg: str,
         exc: BaseException,
         *args,
     ) -> None:
         """trace_id を自動付与して例外をログ出力"""
         trace_id = TraceContext.get_trace_id()
         extra = {"trace_id": trace_id} if trace_id else {}
         logger.error("%s: %s", msg, exc, exc_info=exc, extra=extra)
     ```
- **検証**: `python -c "from src.backend.error_utils import log_exception"` が成功

---

### ステップ 14: F-04（tasks.py 1〜5 箇所目）を修正する
- **対象**: `src/backend/tasks.py` の 1〜5 番目の `except Exception`
- **作業**:
  - 例（85行目）:
    ```python
    except Exception as e:
        logger.error(f"...: {e}", exc_info=True)
    ```
  - 変更後:
    ```python
    from src.backend.error_utils import log_exception
    except (ValueError, RuntimeError, KeyError) as e:
        log_exception(logger, "タスク処理中にエラー", e)
    ```
  - すべての例外型を実際に発生し得る型に絞り込む
- **検証**: `pytest tests/ -k task` がパス

---

### ステップ 15: F-04（tasks.py 6〜10 箇所目）を修正する
- **対象**: `src/backend/tasks.py` の 6〜10 番目の `except Exception`
- **作業**: ステップ 14 と同じパターンで具体的な例外型に狭める
- **検証**: `pytest tests/ -k task` がパス

---

### ステップ 16: F-04（tasks.py 11〜18 箇所目）を修正する
- **対象**: `src/backend/tasks.py` の 11〜18 番目の `except Exception`
- **作業**: ステップ 14 と同じパターン
- **検証**: `pytest tests/ -k task` がパス

---

### ステップ 17: F-04（writing_langgraph.py 全 10 箇所）を修正する
- **対象**: `src/backend/workflows/writing_langgraph.py` の全 `except Exception`
- **作業**: 各箇所で具体的な例外型（`ValueError`, `RuntimeError`, `KeyError`, `json.JSONDecodeError` 等）に狭め、`log_exception` を使用
- **検証**: `pytest tests/ -k writing` がパス

---

### ステップ 18: F-04（database/core.py 全 4 箇所）を修正する
- **対象**: `src/backend/database/core.py` の全 `except Exception`
- **作業**: 各箇所で `sqlalchemy.exc.SQLAlchemyError`, `OSError`, `asyncio.TimeoutError` 等に狭める
- **検証**: `pytest tests/ -k database` がパス

---

### ステップ 19: F-04 の中間コミット
- **作業**: `git add -A && git commit -m "refactor(backend): narrow except Exception and add trace_id logging"`
- **検証**: `git log --oneline -1` でコミット確認

---

### ステップ 20: F-05（commercial_validation.py）を修正する
- **対象**: `src/backend/kakuyomu/commercial_validation.py:141`
- **変更前**:
  ```python
  print(f"Correlation: {corr:.3f}")
  ```
- **変更後**:
  ```python
  logger.info(f"Correlation: {corr:.3f}")
  ```
- **検証**: `grep -n "print" src/backend/kakuyomu/commercial_validation.py` で出力がないこと

---

### ステップ 21: F-05（promptops.py）を修正する
- **対象**: `src/cli/promptops.py` の全 `print` 文
- **変更**: すべて `logger.info(...)` に置換
- **検証**: `grep -n "print" src/cli/promptops.py` で出力がないこと
- **注意**: CLI スクリプトの場合は `click.echo` の方が適切。判断はステップ 22 で行う

---

### ステップ 22: F-05（promptops.py）の CLI 設計を見直す
- **作業**:
  1. `src/cli/promptops.py` が CLI エントリポイント（`__main__`）かどうか確認
  2. CLI なら `click.echo` を使用、ロギング用なら `logger` を使用
  3. 混在している場合は役割を分離
- **検証**: 関数の責務が明確になっていること

---

### ステップ 23: F-06 の DI 化計画を立てる
- **対象**: `src/backend/redis_util.py`
- **作業**:
  1. `config/container.py` の現状を確認:
     ```bash
     grep -n "redis\|Redis" config/container.py | head -30
     ```
  2. 既存の `RedisCacheService` プロバイダを確認
- **検証**: DI コンテナに Redis プロバイダが既にあるか、新規追加かを判定

---

### ステップ 24: F-06 のラッパークラスを作成する
- **対象**: `src/backend/redis_util.py` を段階的に DI 化
- **作業**:
  1. 既存関数を **残し**、`get_redis_client` を内部関数 `_create_client` にリネーム
  2. 新規 `RedisClientFactory` クラスを追加:
     ```python
     from dependency_injector import providers
     from src.services.redis_cache import RedisCacheService

     class RedisClientFactory:
         """DI コンテナ経由で利用する Redis クライアントファクトリ"""

         def __init__(self, url: str, socket_timeout: float = 1.0):
             self._url = url
             self._socket_timeout = socket_timeout

         def __call__(self) -> RedisCacheService | None:
             return self._create()

         def _create(self) -> RedisCacheService | None:
             try:
                 return RedisCacheService.from_url(
                     self._url, socket_timeout=self._socket_timeout
                 )
             except Exception as e:
                 logger.warning(f"Redis unavailable: {e}")
                 return None
     ```
  3. 旧グローバル変数は deprecated ラベルで残す
- **検証**: `python -c "from src.backend.redis_util import RedisClientFactory"` が成功

---

### ステップ 25: F-06 の DI 登録を行う
- **対象**: `config/container.py`
- **作業**:
  1. `RedisClientFactory` を DI コンテナに登録:
     ```python
     from src.backend.redis_util import RedisClientFactory
     redis_factory = providers.Factory(
         RedisClientFactory,
         url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
     )
     ```
  2. 既存の `get_redis_client()` 呼び出し箇所を `grep -rn "get_redis_client\|get_async_redis_client" src/` で列挙
- **検証**: `python -c "from config.container import container; print(container.redis_factory())"` が動作

---

### ステップ 26: F-06 の呼び出し側を段階移行する（前半）
- **対象**: `get_redis_client` の呼び出し箇所のうち、安全な半分
- **作業**:
  1. `routers/` 配下の呼び出しを `container.redis_factory()` 経由に置換
  2. 旧関数は `DeprecationWarning` を発出
- **検証**: `pytest tests/ -k router` がパス

---

### ステップ 27: F-06 の呼び出し側を段階移行する（後半）
- **対象**: 残りの呼び出し箇所
- **作業**: ステップ 26 と同じ
- **検証**: `pytest tests/` が全パス

---

### ステップ 28: F-07 を修正する
- **対象**: `src/backend/engine_utils.py:152-178` の `safe_run_async`
- **変更前**:
  ```python
  with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
      return executor.submit(_worker, coro).result()
  ```
- **変更後**:
  ```python
  # リクエスト毎にスレッドプールを生成せず、
  # 既存ループへコルーチンをスケジュール
  future = asyncio.run_coroutine_threadsafe(coro, loop)
  return future.result()
  ```
- **検証**: `pytest tests/ -k safe_run_async` がパス

---

### ステップ 29: F-07 の `safe_run_async` テストを追加する
- **対象**: `tests/backend/test_safe_run_async.py`（新規）
- **作業**:
  ```python
  import asyncio
  from src.backend.engine_utils import safe_run_async

  def test_runs_coroutine_from_sync_context():
      async def coro():
          return 42
      assert safe_run_async(coro()) == 42

  def test_does_not_create_new_thread_pool_per_call():
      """パフォーマンス回帰防止"""
      import time
      async def coro():
          return None
      start = time.perf_counter()
      for _ in range(100):
          safe_run_async(coro())
      elapsed = time.perf_counter() - start
      assert elapsed < 5.0  # 100回で 5 秒以内
  ```
- **検証**: 新規テストがパス

---

### ステップ 30: F-08 を修正する
- **対象**: `src/backend/kakuyomu/commercial_validation.py:134-141`
- **変更前**:
  ```python
  def run_validation(limit: int = 20, llm_provider=None) -> None:
      works = fetch_top_works(limit)
      corr = asyncio.run(compute_correlation(works, llm_provider=llm_provider))
  ```
- **変更後**:
  ```python
  async def run_validation(limit: int = 20, llm_provider=None) -> float:
      """非同期コンテキストから呼び出す検証関数"""
      works = await asyncio.to_thread(fetch_top_works, limit)
      return await compute_correlation(works, llm_provider=llm_provider)
  ```
- **注意**: 互換性のため旧 `run_validation` は残し、内部で `asyncio.run` を呼び出す wrapper として再エクスポート
- **検証**: `python -c "import inspect; from src.backend.kakuyomu.commercial_validation import run_validation; print(inspect.iscoroutinefunction(run_validation))"` が `True`

---

### ステップ 31: F-08 の CLI エントリポイントを分離する
- **対象**: `src/backend/kakuyomu/commercial_validation.py:143-144`
- **変更**:
  ```python
  if __name__ == "__main__":
      async def _main():
          corr = await run_validation()
          print(f"Correlation: {corr:.3f}")
      asyncio.run(_main())
  ```
- **検証**: `python -m src.backend.kakuyomu.commercial_validation` がエラーなく起動（Playwright 未インストールなら RuntimeError で OK）

---

### ステップ 32: F-09 の archive を調査する
- **作業**:
  1. `du -sh archive/` でサイズ確認
  2. `ls archive/` で内容確認
  3. `git log --oneline -- archive/ | head -5` で履歴確認
- **判定**:
  - 履歴として必要 → そのまま残す（`archive/README.md` に目的を明記）
  - 不要 → `git rm -r archive/` で削除

---

### ステップ 33: F-09 を実行する
- **作業**: ステップ 32 の判定に基づき、`archive/README.md` 追加 or `git rm -r archive/`
- **検証**: `git status` で変更が反映されていること

---

### ステップ 34: 全体の中間コミット
- **作業**:
  ```bash
  git add -A
  git commit -m "refactor: apply code review fixes (cache pattern, id length, logging, DI, print, archive)"
  ```
- **検証**: `git log --oneline -5`

---

### ステップ 35: 品質ゲートの最終確認
- **作業**:
  1. `mypy --strict src 2>&1 | tee /tmp/mypy_after.txt` を実行
  2. `ruff check src 2>&1 | tee /tmp/ruff_after.txt` を実行
  3. `pytest tests/ --cov=src 2>&1 | tee /tmp/pytest_after.txt` を実行
  4. 各ファイルの Before/After を `coverage_review.md` に追記:
     ```markdown
     | 指標 | Before | After | Delta |
     |------|--------|-------|-------|
     | mypy エラー | XX | YY | -ZZ |
     | ruff 違反 | XX | YY | -ZZ |
     | テストカバレッジ | XX% | YY% | +ZZ% |
     | except Exception 数 | 32 | 0 | -32 |
     ```
- **検証**: 全品質ゲートが既知の状態にあること

---

### ステップ 36: ドキュメント更新と PR 作成
- **作業**:
  1. `CHANGELOG.md` の `[Unreleased]` セクションに変更を記載
  2. `code_review_plan.md` の各項目に「✅ 解消」を記載
  3. `git push origin refactor/code-review-fixes`
  4. PR を作成し、レビューを依頼:
     - タイトル: `[REFACTOR] コードレビュー指摘事項の解消`
     - 本文: ステップ 35 の Before/After 表を貼付
- **検証**: PR URL が取得できること

---

## 各ステップの所要時間目安

| ステップ範囲 | 想定工数 | 備考 |
|-------------|---------|------|
| 1〜2 | 0.5h | 準備 |
| 3〜8 | 2h | F-01, F-02（TDD 含む） |
| 9〜11 | 1h | F-03 |
| 12〜19 | 4h | F-04（最大ボリューム） |
| 20〜22 | 1h | F-05 |
| 23〜27 | 3h | F-06（DI 化） |
| 28〜29 | 1.5h | F-07 |
| 30〜31 | 1h | F-08 |
| 32〜33 | 0.5h | F-09 |
| 34 | 0.5h | コミット |
| 35〜36 | 1h | 検証・ドキュメント |
| **合計** | **約 16h** | 1〜2 営業日 |

## リスクと対策

| リスク | 対策 |
|--------|------|
| F-04 で例外型を絞りすぎて既存テストが失敗 | 各ステップ 14〜18 で必ず `pytest` を実行し、段階的に進める |
| F-06 の DI 化で `get_redis_client` 呼び出し側が多い | `DeprecationWarning` を 1 リリース挟み、段階移行 |
| F-07 の変更でデッドロック | ステップ 29 のパフォーマンステストに加え、ループ内呼び出しの単体テストを追加 |
| F-08 の互換性破壊 | 旧 `run_validation` を wrapper として残す（ステップ 30） |

## ロールバック計画

各ステップは独立したコミット（または一連のコミット）として実装する。
問題発生時は `git revert <commit-hash>` で該当ステップのみ取り消せる粒度を維持する。

特に以下は要注意：
- ステップ 10（UUID 長さ変更）: 既存 ID と互換性問題があれば `length=12` の旧関数を `generate_prefixed_id_legacy` として残す
- ステップ 24〜27（DI 化）: 旧グローバル関数を deprecated として残し、緊急時に戻せるようにする

## 低性能 LLM 向け実装メモ

各ステップの実装時は以下の情報をプロンプトに含めると成功率が高まる：

1. **変更前コードの 5 行前と 5 行後**を必ずコピー
2. **変更後の完全コードブロック**を提示（差分ではなく全体）
3. **検証コマンドを 1 ステップ 1 個**に限定
4. **依存 import** を新規追加する場合は、import ブロック全体を提示
5. **docstring** は日本語で 1〜2 行に統一（過度に長くしない）

例（ステップ 4 を LLM に依頼する場合のプロンプト）:
```
src/services/redis_cache.py の 622-636 行目にある
invalidate_task_type メソッドのパターン文字列を修正してください。

【変更箇所のみ提示】
変更前:
    pattern = f"prompt:*:*:*:*:{task_type}:*"
変更後:
    pattern = f"prompt:*:*:*:{task_type}:*"

【理由】
実キーは "prompt:{template}:{model}:{version}:{task_type}:{hash}" の
6 セクション構成です。パターンのワイルドカード数を 5 から 4 に
減らす必要があります。

【検証】
pytest tests/services/test_redis_cache_invalidate.py -v
```
