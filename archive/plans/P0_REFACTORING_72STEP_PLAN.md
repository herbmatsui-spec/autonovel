# P0リファクタリング 72ステップ実装計画書

> **目的**: 改善案1〜3（import drift解消・API重複解消・server.py router分割）を、低性能LLMでも確実に実装できるよう72の小ステップに分割した計画書。
> **前提**: 各ステップは1ステップ＝1コミット相当。各ステップ完了後に必ず完了判定を確認し、緑のまま次へ進む。

---

## 📊 現状サマリー（2026-07-11時点）

| 改善案 | 状態 | 備考 |
|--------|------|------|
| 案1: import drift 5件 | **既に解消済み** | `pytest --collect-only` が438テスト・エラーゼロで完了 |
| 案2: narrative_metrics重複 | **未対応** | server.py:136（query版）と server.py:850（path版）が重複 |
| 案3: server.py router分割 | **未対応** | server.py 1001行・40エンドポイント |

### 既存エンドポイント分類（40件）

| router | エンドポイント | 行範囲 |
|--------|---------------|--------|
| health | `GET /health` | 112-133 |
| metrics | `GET /api/books/{id}/narrative_metrics`（旧query版）, `GET /api/narrative_metrics/{id}/{branch_id}`（path版） | 136-150, 850-857 |
| books | `GET /api/books`, `GET /api/books/{id}`, `DELETE /api/books/{id}`, `GET /api/books/{id}/issues` | 159-200, 845-848 |
| plots | `GET /api/plots/{id}`, `POST /api/plots/plan_generation`, `POST /api/plots/expand`, `POST /api/plots/expand_candidates`, `POST /api/plots/rebuild`, `POST /api/plots/audit` | 202-217, 591-603, 673-711, 769-788 |
| episodes | `POST /api/episodes/retry_failed`, `POST /api/episodes/generate`, `POST /api/episodes/generate_candidates` | 605-671 |
| tasks | `GET /api/tasks/{id}/status`, `GET /api/tasks/{id}/stream`, `POST /api/tasks/{id}/stop` | 439-519 |
| patches | `GET /api/patches/{id}/pending`, `POST /api/patches/{id}/approve`, `POST /api/patches/{id}/reject`, `POST /api/patches/{id}/edit` | 262-391 |
| issues | `POST /api/issues/{id}/resolve` | 862-924 |
| marketing | `POST /api/marketing/generate`, `POST /api/marketing/export_package/{id}`, `GET /api/marketing/export_package/{id}` | 810-842 |
| prompt_versions | `GET /api/prompt_versions/{id}`, `POST /api/prompt_versions/{id}/rollback` | 394-436 |
| chapters | `GET /api/chapters/{id}`, `POST /api/chapters/import` | 219-232, 790-808 |
| bibles | `GET /api/bibles/{id}` | 234-246 |
| misc | `GET /api/optimization_history/{id}`, `POST /api/refine_erotic`, `POST /api/easy_mode/generate`, `POST /api/critique/optimize`, `GET/POST/DELETE /api/prompt-metrics` | 248-259, 545-563, 566-589, 750-766, 934-998 |

### テストのapp参照方法
- `tests/test_sse.py:23` → `from src.backend.server import app`
- **制約**: router分割後も `src/backend/server.py` に `app` オブジェクトが残る必要がある

---

## 🏗️ 全体設計

### ディレクトリ構造（目標）

```
src/backend/
├── server.py              # app定義 + lifespan/CORS/middleware + include_router のみ（目標: 200行以下）
├── routers/
│   ├── __init__.py         # 全routerを再エクスポート
│   ├── health.py           # /health
│   ├── books.py            # /api/books/*
│   ├── plots.py            # /api/plots/*
│   ├── episodes.py         # /api/episodes/*
│   ├── tasks.py            # /api/tasks/*
│   ├── patches.py          # /api/patches/*
│   ├── issues.py           # /api/issues/*
│   ├── marketing.py        # /api/marketing/*
│   ├── prompt_versions.py  # /api/prompt_versions/*
│   ├── metrics.py          # /api/narrative_metrics/* + /api/prompt-metrics/*
│   ├── chapters.py         # /api/chapters/*
│   ├── bibles.py           # /api/bibles/*
│   └── misc.py             # /api/optimization_history, /api/refine_erotic, /api/easy_mode, /api/critique
```

### 共通依存パターン

各routerファイルは以下の構造を持つ:

```python
# routers/<name>.py
"""<name> API routes."""
import json
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter
from sqlalchemy import select

from config.container import Container
from src.backend.database import UnitOfWork
from src.core.observability import TraceContext

router = APIRouter(prefix="/api/<name>", tags=["<name>"])

# ... エンドポイント定義 ...
```

---

## 📋 ステップ一覧（72ステップ）

### フェーズ0: 事前検証（ステップ1〜3）

#### ステップ1: ベースラインテスト実行
- **前提**: なし
- **作業**: `python -m pytest --collect-only -q` を実行し、438テストがエラーゼロで収集されることを確認
- **完了判定**: "438 tests collected" が表示され、ERRORが0件
- **想定エラー**: ImportErrorが出る場合 → 案1が未解消。本計画の案1セクション（ステップ4〜9）を先に実行

#### ステップ2: ベースラインテスト全文実行
- **前提**: ステップ1完了
- **作業**: `python -m pytest -x -q --timeout=60` を実行し、現状の通過/失敗状況を記録
- **完了判定**: テストが完了（通過数・失敗数をメモ）
- **想定エラー**: 一部テストがタイムアウト/失敗する場合がある → そのテスト名を記録し、以降のステップで「既存の失敗」として扱う（リファクタリングで新規失敗を生まないことが基準）

#### ステップ3: バックアップ作成
- **前提**: ステップ2完了
- **作業**: `Copy-Item src/backend/server.py src/backend/server.py.bak` を実行
- **完了判定**: `src/backend/server.py.bak` が存在する
- **想定エラー**: なし

---

### フェーズ1: 改善案1 — import drift 最終確認（ステップ4〜9）

> **注意**: 現状確認の結果、案1の3項目は既に解消済み。しかし念のため実体を確認し、未対応項目があれば修正する。

#### ステップ4: config/archetypes.py 構文確認
- **前提**: ステップ3完了
- **作業**: `python -c "import config.archetypes; print('OK')"` を実行
- **完了判定**: "OK" が表示される（構文エラーなし）
- **想定エラー**: SyntaxErrorが出る場合 → 以下を `config/archetypes.py` の先頭に正しいPython構文で記述:
  ```python
  CHEAT_DESCRIPTIONS = {
      "CRAFTY_PLANNING": "Enemies anticipate and counter your strategic moves.",
      "BETRAYAL": "Allies suddenly turn hostile.",
      "STALEMATE": "Enemy forces become unbreakably equal in power.",
  }
  ```

#### ステップ5: src/core/observability.py 関数存在確認
- **前提**: ステップ4完了
- **作業**: `python -c "from src.core.observability import with_trace_context, track_llm_call; print('OK')"` を実行
- **完了判定**: "OK" が表示される
- **想定エラー**: ImportErrorが出る場合 → `src/core/observability.py` に以下を追記:
  ```python
  def with_trace_context(func):
      """Trace context decorator."""
      return func

  def track_llm_call(func):
      """LLM call tracking decorator."""
      return func
  ```

#### ステップ6: src/agents/audit.py InternalLogicValidator確認
- **前提**: ステップ5完了
- **作業**: `python -c "from src.agents.audit import InternalLogicValidator; print('OK')"` を実行
- **完了判定**: "OK" が表示される
- **想定エラー**: ImportErrorが出る場合 → `src/agents/audit.py` に以下を追記（109行目以降に既存）:
  ```python
  class InternalLogicValidator:
      """内部ロジック整合性検証エージェント（スタブ）。"""
      def __init__(self, repo=None, llm=None, ctx_mgr=None, pm=None, **kwargs):
          self.repo = repo
          self.ctx_mgr = ctx_mgr
          self.prompt_manager = pm
          if "generate_json" in kwargs:
              self.llm = kwargs["generate_json"]
          elif llm is not None:
              self.llm = llm
          else:
              self.llm = None
          self.wave_analyzer = None

      async def validate_alibi_and_timeline(self, blueprint: str, script: str):
          return True, []

      async def check_information_asymmetry(self, past_info: str, current_info: str):
          return True, []
  ```

#### ステップ7: pytest --collect-only 再確認
- **前提**: ステップ6完了
- **作業**: `python -m pytest --collect-only -q` を実行
- **完了判定**: "438 tests collected" でエラーゼロ
- **想定エラー**: ステップ4〜6で修正した場合は収集数が変わる可能性 → エラーゼロならOK

#### ステップ8: CI緑化確認（ローカル）
- **前提**: ステップ7完了
- **作業**: `python -m pytest -x -q --timeout=60` を実行し、ステップ2と同じ結果であることを確認
- **完了判定**: ステップ2と同じ通過/失敗数（新規失敗なし）
- **想定エラー**: 新規失敗が出た場合 → ステップ4〜6の修正が影響。差分を確認し元に戻す

#### ステップ9: 案1完了判定
- **前提**: ステップ8完了
- **作業**: `pytest --collect-only` がエラーゼロであることを文書化
- **完了判定**: ✅ 案1完了（CI緑化）
- **想定エラー**: なし

---

### フェーズ2: 改善案2 — narrative_metrics重複解消（ステップ10〜18）

#### ステップ10: 重複ルートの現状確認
- **前提**: ステップ9完了
- **作業**: server.pyの136行目と850行目を確認し、両方が `narrative_metrics` に関連することを確認
- **完了判定**: 以下の2つのルートが存在することを確認:
  - 136行: `@app.get("/api/books/{book_id}/narrative_metrics")` （旧query版）
  - 850行: `@app.get("/api/narrative_metrics/{book_id}/{branch_id}")` （新path版）
- **想定エラー**: なし

#### ステップ11: frontend/api.ts の使用ルート確認
- **前提**: ステップ10完了
- **作業**: `frontend/src/api.ts:298-300` を確認し、path版（`/narrative_metrics/${book_id}/${branch_id}`）を使用していることを確認
- **完了判定**: path版を使用していることを確認
- **想定エラー**: なし

#### ステップ12: Streamlit側の使用ルート確認
- **前提**: ステップ11完了
- **作業**: `streamlit_app/` 配下で `narrative_metrics` を検索し、使用箇所を特定
- **完了判定**: Streamlit側の使用箇所（0件またはpath版）を確認
- **想定エラー**: なし（現状0件）

#### ステップ13: 旧query版ルートの非推奨化
- **前提**: ステップ12完了
- **作業**: server.py:136 の `get_narrative_metrics` 関数に `@deprecated` デコレータとdocstringを追加:
  ```python
  from fastapi import deprecated  # 先頭import部に追加

  @app.get("/api/books/{book_id}/narrative_metrics", deprecated=True, tags=["metrics"])
  async def get_narrative_metrics(book_id: int, branch_id: int = 1, ep_num: Optional[int] = None):
      """[非推奨] 新path版 /api/narrative_metrics/{book_id}/{branch_id} を使用してください。"""
      # ... 既存実装 ...
  ```
- **完了判定**: server.pyが構文エラーなくインポート可能
- **想定エラー**: `from fastapi import deprecated` でImportError → FastAPIバージョン確認。`deprecated` はFastAPI 0.95+ で利用可能。不可場合はdocstringに `[非推奨]` を明記するだけ

#### ステップ14: 旧query版ルートの動作確認
- **前提**: ステップ13完了
- **作業**: `python -c "from src.backend.server import app; print('OK')"` を実行
- **完了判定**: "OK" が表示される
- **想定エラー**: ImportError → ステップ13の構文を確認

#### ステップ15: OpenAPI仕様の重複確認
- **前提**: ステップ14完了
- **作業**: `python -c "from src.backend.server import app; import json; print(json.dumps([p for p in app.openapi()['paths'] if 'narrative_metrics' in p], indent=2))"` を実行
- **完了判定**: 2つのパスが表示されることを確認（旧query版は `deprecated: true` 付き）
- **想定エラー**: なし

#### ステップ16: デッドコード（858行）の確認
- **前提**: ステップ15完了
- **作業**: server.py:857-860 を確認。857行の `return metrics` の後、858-860行に到達不能コードがあることを確認:
  ```python
  857:        return metrics
  858:    async with UnitOfWork(Container.db()) as uow:  # ← 到達不能
  859:        issues = await uow.audit.get_issues_by_book(book_id)
  860:    return issues
  ```
- **完了判定**: 858-860行がデッドコードであることを確認
- **想定エラー**: なし

#### ステップ17: デッドコードの削除
- **前提**: ステップ16完了
- **作業**: server.py:858-860 の3行を削除:
  ```python
  # 削除前:
      async with UnitOfWork(Container.db()) as uow:
          metrics = await uow.narrative_metrics.get_trend_metrics(book_id, branch_id)
          return metrics
      async with UnitOfWork(Container.db()) as uow:      # ← 削除
          issues = await uow.audit.get_issues_by_book(book_id)  # ← 削除
      return issues                                          # ← 削除

  # 削除後:
      async with UnitOfWork(Container.db()) as uow:
          metrics = await uow.narrative_metrics.get_trend_metrics(book_id, branch_id)
          return metrics
  ```
- **完了判定**: server.pyが構文エラーなくインポート可能
- **想定エラー**: なし

#### ステップ18: 案2完了判定
- **前提**: ステップ17完了
- **作業**: `python -m pytest --collect-only -q` を実行し、エラーゼロを確認
- **完了判定**: ✅ 案2完了（重複ルートの非推奨化・デッドコード削除）
- **想定エラー**: なし

---

### フェーズ3: 改善案3 — router分割準備（ステップ19〜24）

#### ステップ19: routersディレクトリ作成
- **前提**: ステップ18完了
- **作業**: `src/backend/routers/` ディレクトリを作成
- **完了判定**: ディレクトリが存在する
- **想定エラー**: なし

#### ステップ20: routers/__init__.py 作成
- **前提**: ステップ19完了
- **作業**: `src/backend/routers/__init__.py` を作成（空ファイル）
- **完了判定**: ファイルが存在する
- **想定エラー**: なし

#### ステップ21: 共通依存モジュールの確認
- **前提**: ステップ20完了
- **作業**: server.pyのimport部（1-31行）を確認し、各routerで必要なimportを把握:
  - `json`, `time`, `logging`, `os`, `sys`
  - `from typing import Any, Dict, Optional`
  - `from pydantic import BaseModel`
  - `from sqlalchemy import select`
  - `from config.container import Container`
  - `from src.backend.database import UnitOfWork`
  - `from src.core.observability import TraceContext`
  - `from src.models.api_schemas import ...`（各routerで必要なスキーマ）
- **完了判定**: import一覧をメモ
- **想定エラー**: なし

#### ステップ22: api_schemasのインポート一覧確認
- **前提**: ステップ21完了
- **作業**: `src/models/api_schemas.py` を確認し、各スキーマが存在することを確認:
  - EasyModeRequest, EpisodeGenerateRequest, EpisodeGenerateCandidatesRequest
  - PlanGenerationRequest, RetryFailedRequest, PlotExpandRequest
  - PlotExpandCandidatesRequest, PlotRebuildRequest, CritiqueOptimizeRequest
  - AuditPlanRequest, ChapterImportRequest, MarketingGenerateRequest
  - RefineEroticRequest, PatchActionRequest, PatchEditRequest
  - RollbackRequest, ResolveIssueRequest
- **完了判定**: 全スキーマがインポート可能
- **想定エラー**: 一部スキーマが存在しない → `src/models/api_schemas.py` に追加

#### ステップ23: _get_engine ヘルパーの移動先決定
- **前提**: ステップ22完了
- **作業**: `_get_engine` 関数（154-157行）をどこに置くか決定。`src/backend/engine_helpers.py` に移動する方針とする
- **完了判定**: 移動先を決定
- **想定エラー**: なし

#### ステップ24: _create_task ヘルパーの移動先決定
- **前提**: ステップ23完了
- **作業**: `_create_task` 関数（523-543行）をどこに置くか決定。`src/backend/task_helpers.py` に移動する方針とする
- **完了判定**: 移動先を決定
- **想定エラー**: なし

---

### フェーズ4: ヘルパーモジュール作成（ステップ25〜28）

#### ステップ25: engine_helpers.py 作成
- **前提**: ステップ24完了
- **作業**: `src/backend/engine_helpers.py` を作成:
  ```python
  """Engine helper functions."""
  from src.backend.engine import UltimateHegemonyEngine
  from config.container import Container


  def get_engine(api_key: str) -> UltimateHegemonyEngine:
      """APIキーからエンジンインスタンスを生成する。"""
      from google import genai
      client = genai.Client(api_key=api_key)
      return UltimateHegemonyEngine(api_key=api_key, client=client, db_manager=Container.db())
  ```
- **完了判定**: `python -c "from src.backend.engine_helpers import get_engine; print('OK')"` が成功
- **想定エラー**: ImportError → `UltimateHegemonyEngine` のimportパスを確認

#### ステップ26: task_helpers.py 作成
- **前提**: ステップ25完了
- **作業**: `src/backend/task_helpers.py` を作成:
  ```python
  """Task state helper functions."""
  import json
  import time

  from config.container import Container


  async def create_task(task_id: str, message: str, total_steps: int = 1) -> None:
      """タスクの初期状態をDBに保存する。"""
      db = Container.db()
      initial_state = {
          "is_running": True,
          "current_step": 0,
          "total_steps": total_steps,
          "message": message,
          "sub_message": "キューの待機中",
          "streaming_text": "",
          "logs": [f"[{time.strftime('%H:%M:%S')}] 🚀 タスクを登録しました。"],
          "error": None,
          "result_data": None,
          "token_usage": {"prompt": 0, "completion": 0, "calls": 0},
          "start_time": time.time(),
          "last_updated": time.time()
      }
      await db.save_internal_state(
          f"task_status:{task_id}",
          json.dumps(initial_state),
          time.strftime('%Y-%m-%d %H:%M:%S')
      )
  ```
- **完了判定**: `python -c "from src.backend.task_helpers import create_task; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ27: ヘルパーモジュールの動作確認
- **前提**: ステップ26完了
- **作業**: `python -c "from src.backend.engine_helpers import get_engine; from src.backend.task_helpers import create_task; print('OK')"` を実行
- **完了判定**: "OK" が表示される
- **想定エラー**: なし

#### ステップ28: server.pyの_get_engineをヘルパーに置き換え
- **前提**: ステップ27完了
- **作業**: server.py:154-157 の `_get_engine` を `engine_helpers.get_engine` のエイリアスに変更:
  ```python
  # 変更前:
  def _get_engine(api_key: str) -> UltimateHegemonyEngine:
      from google import genai
      client = genai.Client(api_key=api_key)
      return UltimateHegemonyEngine(api_key=api_key, client=client, db_manager=Container.db())

  # 変更後:
  from src.backend.engine_helpers import get_engine as _get_engine
  ```
- **完了判定**: `python -c "from src.backend.server import app; print('OK')"` が成功
- **想定エラー**: なし

---

### フェーズ5: health router作成（ステップ29〜31）

#### ステップ29: routers/health.py 作成
- **前提**: ステップ28完了
- **作業**: `src/backend/routers/health.py` を作成:
  ```python
  """Health check endpoint."""
  from fastapi import APIRouter

  from config.container import Container

  router = APIRouter(tags=["health"])


  @router.get("/health")
  async def health_check():
      db_status = "ok"
      try:
          db_manager = Container.db()
          async with db_manager.engine.acquire() as conn:
              await conn.execute("SELECT 1")
      except Exception:
          db_status = "error"

      worker_status = "ok"
      try:
          from src.backend.tasks import huey
          huey.pending_count()
      except Exception:
          worker_status = "error"

      return {
          "status": "ok",
          "database": db_status,
          "worker": worker_status
      }
  ```
- **完了判定**: `python -c "from src.backend.routers.health import router; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ30: server.pyにhealth routerをinclude
- **前提**: ステップ29完了
- **作業**: server.pyのhealth_check関数（112-133行）を削除し、代わりに `app.include_router` を追加:
  ```python
  # server.pyの末尾（app定義後）に追加:
  from src.backend.routers.health import router as health_router
  app.include_router(health_router)
  ```
- **完了判定**: `python -c "from src.backend.server import app; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ31: health routerの動作確認
- **前提**: ステップ30完了
- **作業**: `python -m pytest --collect-only -q` を実行し、エラーゼロを確認
- **完了判定**: 438テスト収集・エラーゼロ
- **想定エラー**: テストが減る場合 → health関連テストのimport先を確認

---

### フェーズ6: books router作成（ステップ32〜35）

#### ステップ32: routers/books.py 作成
- **前提**: ステップ31完了
- **作業**: `src/backend/routers/books.py` を作成。server.py:159-200, 845-848 のエンドポイントを移行:
  ```python
  """Books API routes."""
  from fastapi import APIRouter

  from config.container import Container
  from src.backend.database import UnitOfWork

  router = APIRouter(prefix="/api/books", tags=["books"])


  @router.get("")
  async def list_books():
      async with UnitOfWork(Container.db()) as uow:
          books = await uow.books.get_all_books()
      return [
          {
              "id": b.id,
              "title": b.title,
              "genre": b.genre,
              "concept": b.concept,
              "synopsis": b.synopsis,
              "target_eps": b.target_eps,
              "cumulative_stress": b.cumulative_tension,
              "created_at": b.created_at
          }
          for b in books
      ]


  @router.get("/{book_id}")
  async def get_book(book_id: int):
      async with UnitOfWork(Container.db()) as uow:
          b = await uow.books.get_book(book_id)
      if not b:
          from src.core.exceptions import NotFoundError
          raise NotFoundError("Book not found", resource_type="Book", resource_id=str(book_id))
      return {
          "id": b.id,
          "title": b.title,
          "genre": b.genre,
          "concept": b.concept,
          "synopsis": b.synopsis,
          "target_eps": b.target_eps,
          "cumulative_stress": b.cumulative_tension,
          "created_at": b.created_at
      }


  @router.delete("/{book_id}")
  async def delete_book(book_id: int):
      async with UnitOfWork(Container.db()) as uow:
          await uow.books.delete_book(book_id)
      return {"message": "Book deleted successfully"}


  @router.get("/{book_id}/issues")
  async def get_issues(book_id: int):
      async with UnitOfWork(Container.db()) as uow:
          return await uow.issues.get_book_issues(book_id)
  ```
- **完了判定**: `python -c "from src.backend.routers.books import router; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ33: server.pyからbooksエンドポイント削除
- **前提**: ステップ32完了
- **作業**: server.py:159-200, 845-848 のエンドポイントを削除
- **完了判定**: server.pyが構文エラーなくインポート可能
- **想定エラー**: なし

#### ステップ34: server.pyにbooks routerをinclude
- **前提**: ステップ33完了
- **作業**: server.pyの末尾に追加:
  ```python
  from src.backend.routers.books import router as books_router
  app.include_router(books_router)
  ```
- **完了判定**: `python -c "from src.backend.server import app; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ35: books routerの動作確認
- **前提**: ステップ34完了
- **作業**: `python -m pytest --collect-only -q` を実行
- **完了判定**: 438テスト収集・エラーゼロ
- **想定エラー**: なし

---

### フェーズ7: plots router作成（ステップ36〜39）

#### ステップ36: routers/plots.py 作成
- **前提**: ステップ35完了
- **作業**: `src/backend/routers/plots.py` を作成。server.py:202-217, 591-603, 673-711, 769-788 のエンドポイントを移行:
  ```python
  """Plots API routes."""
  import time

  from fastapi import APIRouter

  from config.container import Container
  from src.backend.database import UnitOfWork
  from src.backend.engine_helpers import get_engine
  from src.backend.task_helpers import create_task
  from src.backend.tasks import execute_service_workflow
  from src.core.observability import TraceContext
  from src.models.api_schemas import (
      PlanGenerationRequest, PlotExpandRequest, PlotExpandCandidatesRequest,
      PlotRebuildRequest, AuditPlanRequest,
  )

  router = APIRouter(prefix="/api/plots", tags=["plots"])


  @router.get("/{book_id}")
  async def get_plots(book_id: int):
      # ... server.py:202-217 の実装をコピー ...


  @router.post("/plan_generation")
  async def plan_generation(req: PlanGenerationRequest):
      # ... server.py:591-603 の実装をコピー ...


  @router.post("/expand")
  async def expand_plots(req: PlotExpandRequest):
      # ... server.py:673-691 の実装をコピー ...


  @router.post("/expand_candidates")
  async def expand_plots_candidates(req: PlotExpandCandidatesRequest):
      # ... server.py:693-711 の実装をコピー ...


  @router.post("/rebuild")
  async def rebuild_plots(req: PlotRebuildRequest):
      # ... server.py:713-748 の実装をコピー ...


  @router.post("/audit")
  async def audit_plan(req: AuditPlanRequest):
      # ... server.py:769-788 の実装をコピー ...
  ```
- **完了判定**: `python -c "from src.backend.routers.plots import router; print('OK')"` が成功
- **想定エラー**: ImportError → import文を確認

#### ステップ37: server.pyからplotsエンドポイント削除
- **前提**: ステップ36完了
- **作業**: server.py:202-217, 591-603, 673-711, 769-788 のエンドポイントを削除
- **完了判定**: server.pyが構文エラーなくインポート可能
- **想定エラー**: なし

#### ステップ38: server.pyにplots routerをinclude
- **前提**: ステップ37完了
- **作業**: server.pyの末尾に追加:
  ```python
  from src.backend.routers.plots import router as plots_router
  app.include_router(plots_router)
  ```
- **完了判定**: `python -c "from src.backend.server import app; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ39: plots routerの動作確認
- **前提**: ステップ38完了
- **作業**: `python -m pytest --collect-only -q` を実行
- **完了判定**: 438テスト収集・エラーゼロ
- **想定エラー**: なし

---

### フェーズ8: episodes router作成（ステップ40〜43）

#### ステップ40: routers/episodes.py 作成
- **前提**: ステップ39完了
- **作業**: `src/backend/routers/episodes.py` を作成。server.py:605-671 のエンドポイントを移行:
  ```python
  """Episodes API routes."""
  import time

  from fastapi import APIRouter

  from src.backend.task_helpers import create_task
  from src.backend.tasks import execute_service_workflow
  from src.core.observability import TraceContext
  from src.models.api_schemas import (
      EpisodeGenerateRequest, EpisodeGenerateCandidatesRequest, RetryFailedRequest,
  )

  router = APIRouter(prefix="/api/episodes", tags=["episodes"])


  @router.post("/retry_failed")
  async def retry_failed_episodes(req: RetryFailedRequest):
      # ... server.py:605-621 の実装をコピー ...


  @router.post("/generate")
  async def generate_episodes(req: EpisodeGenerateRequest):
      # ... server.py:623-646 の実装をコピー ...


  @router.post("/generate_candidates")
  async def generate_episodes_candidates(req: EpisodeGenerateCandidatesRequest):
      # ... server.py:648-671 の実装をコピー ...
  ```
- **完了判定**: `python -c "from src.backend.routers.episodes import router; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ41: server.pyからepisodesエンドポイント削除
- **前提**: ステップ40完了
- **作業**: server.py:605-671 のエンドポイントを削除
- **完了判定**: server.pyが構文エラーなくインポート可能
- **想定エラー**: なし

#### ステップ42: server.pyにepisodes routerをinclude
- **前提**: ステップ41完了
- **作業**: server.pyの末尾に追加:
  ```python
  from src.backend.routers.episodes import router as episodes_router
  app.include_router(episodes_router)
  ```
- **完了判定**: `python -c "from src.backend.server import app; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ43: episodes routerの動作確認
- **前提**: ステップ42完了
- **作業**: `python -m pytest --collect-only -q` を実行
- **完了判定**: 438テスト収集・エラーゼロ
- **想定エラー**: なし

---

### フェーズ9: tasks router作成（ステップ44〜47）

#### ステップ44: routers/tasks.py 作成
- **前提**: ステップ43完了
- **作業**: `src/backend/routers/tasks.py` を作成。server.py:439-519 のエンドポイントを移行:
  ```python
  """Tasks API routes."""
  import json
  import time

  from fastapi import APIRouter
  from sqlalchemy import select

  from config.container import Container
  from src.core.observability import TraceContext

  router = APIRouter(prefix="/api/tasks", tags=["tasks"])


  @router.get("/{task_id}/status")
  async def get_task_status(task_id: str):
      # ... server.py:439-461 の実装をコピー ...


  @router.get("/{task_id}/stream")
  async def stream_task_status(task_id: str):
      # ... server.py:463-476 の実装をコピー ...


  @router.post("/{task_id}/stop")
  async def stop_task(task_id: str):
      # ... server.py:478-519 の実装をコピー ...
  ```
- **完了判定**: `python -c "from src.backend.routers.tasks import router; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ45: server.pyからtasksエンドポイント削除
- **前提**: ステップ44完了
- **作業**: server.py:439-519 のエンドポイントを削除
- **完了判定**: server.pyが構文エラーなくインポート可能
- **想定エラー**: なし

#### ステップ46: server.pyにtasks routerをinclude
- **前提**: ステップ45完了
- **作業**: server.pyの末尾に追加:
  ```python
  from src.backend.routers.tasks import router as tasks_router
  app.include_router(tasks_router)
  ```
- **完了判定**: `python -c "from src.backend.server import app; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ47: tasks routerの動作確認
- **前提**: ステップ46完了
- **作業**: `python -m pytest --collect-only -q` を実行
- **完了判定**: 438テスト収集・エラーゼロ
- **想定エラー**: なし

---

### フェーズ10: patches router作成（ステップ48〜51）

#### ステップ48: routers/patches.py 作成
- **前提**: ステップ47完了
- **作業**: `src/backend/routers/patches.py` を作成。server.py:262-391 のエンドポイントを移行:
  ```python
  """Patches API routes."""
  from typing import Optional

  from fastapi import APIRouter
  from sqlalchemy import select

  from config.container import Container
  from src.backend.database import UnitOfWork
  from src.models.api_schemas import PatchActionRequest, PatchEditRequest

  router = APIRouter(prefix="/api/patches", tags=["patches"])


  @router.get("/{book_id}/pending")
  async def get_pending_patches(book_id: int):
      # ... server.py:262-266 の実装をコピー ...


  @router.post("/{patch_id}/approve")
  async def approve_patch(patch_id: int, req: Optional[PatchActionRequest] = None):
      # ... server.py:269-329 の実装をコピー ...


  @router.post("/{patch_id}/reject")
  async def reject_patch(patch_id: int, req: Optional[PatchActionRequest] = None):
      # ... server.py:331-347 の実装をコピー ...


  @router.post("/{patch_id}/edit")
  async def edit_patch(patch_id: int, req: PatchEditRequest):
      # ... server.py:349-391 の実装をコピー ...
  ```
- **完了判定**: `python -c "from src.backend.routers.patches import router; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ49: server.pyからpatchesエンドポイント削除
- **前提**: ステップ48完了
- **作業**: server.py:262-391 のエンドポイントを削除
- **完了判定**: server.pyが構文エラーなくインポート可能
- **想定エラー**: なし

#### ステップ50: server.pyにpatches routerをinclude
- **前提**: ステップ49完了
- **作業**: server.pyの末尾に追加:
  ```python
  from src.backend.routers.patches import router as patches_router
  app.include_router(patches_router)
  ```
- **完了判定**: `python -c "from src.backend.server import app; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ51: patches routerの動作確認
- **前提**: ステップ50完了
- **作業**: `python -m pytest --collect-only -q` を実行
- **完了判定**: 438テスト収集・エラーゼロ
- **想定エラー**: なし

---

### フェーズ11: issues router作成（ステップ52〜55）

#### ステップ52: routers/issues.py 作成
- **前提**: ステップ51完了
- **作業**: `src/backend/routers/issues.py` を作成。server.py:862-924 のエンドポイントを移行:
  ```python
  """Issues API routes."""
  import json
  import time

  from fastapi import APIRouter

  from config.container import Container
  from src.backend.database import UnitOfWork
  from src.models.api_schemas import ResolveIssueRequest

  router = APIRouter(prefix="/api/issues", tags=["issues"])


  @router.post("/{issue_id}/resolve")
  async def resolve_issue(issue_id: int, req: ResolveIssueRequest):
      # ... server.py:862-924 の実装をコピー ...
  ```
- **完了判定**: `python -c "from src.backend.routers.issues import router; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ53: server.pyからissuesエンドポイント削除
- **前提**: ステップ52完了
- **作業**: server.py:862-924 のエンドポイントを削除
- **完了判定**: server.pyが構文エラーなくインポート可能
- **想定エラー**: なし

#### ステップ54: server.pyにissues routerをinclude
- **前提**: ステップ53完了
- **作業**: server.pyの末尾に追加:
  ```python
  from src.backend.routers.issues import router as issues_router
  app.include_router(issues_router)
  ```
- **完了判定**: `python -c "from src.backend.server import app; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ55: issues routerの動作確認
- **前提**: ステップ54完了
- **作業**: `python -m pytest --collect-only -q` を実行
- **完了判定**: 438テスト収集・エラーゼロ
- **想定エラー**: なし

---

### フェーズ12: marketing router作成（ステップ56〜59）

#### ステップ56: routers/marketing.py 作成
- **前提**: ステップ55完了
- **作業**: `src/backend/routers/marketing.py` を作成。server.py:810-842 のエンドポイントを移行:
  ```python
  """Marketing API routes."""
  import time

  from fastapi import APIRouter
  from pydantic import BaseModel

  from src.backend.engine_helpers import get_engine
  from src.backend.task_helpers import create_task
  from src.backend.tasks import execute_service_workflow
  from src.core.observability import TraceContext
  from src.models.api_schemas import MarketingGenerateRequest

  router = APIRouter(prefix="/api/marketing", tags=["marketing"])


  @router.post("/generate")
  async def generate_marketing(req: MarketingGenerateRequest):
      # ... server.py:810-826 の実装をコピー ...


  @router.post("/export_package/{book_id}")
  async def export_package(book_id: int, api_key_req: BaseModel):
      # ... server.py:828-831 の実装をコピー ...


  @router.get("/export_package/{book_id}")
  async def export_package_get(book_id: int, api_key: str):
      # ... server.py:833-842 の実装をコピー ...
  ```
- **完了判定**: `python -c "from src.backend.routers.marketing import router; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ57: server.pyからmarketingエンドポイント削除
- **前提**: ステップ56完了
- **作業**: server.py:810-842 のエンドポイントを削除
- **完了判定**: server.pyが構文エラーなくインポート可能
- **想定エラー**: なし

#### ステップ58: server.pyにmarketing routerをinclude
- **前提**: ステップ57完了
- **作業**: server.pyの末尾に追加:
  ```python
  from src.backend.routers.marketing import router as marketing_router
  app.include_router(marketing_router)
  ```
- **完了判定**: `python -c "from src.backend.server import app; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ59: marketing routerの動作確認
- **前提**: ステップ58完了
- **作業**: `python -m pytest --collect-only -q` を実行
- **完了判定**: 438テスト収集・エラーゼロ
- **想定エラー**: なし

---

### フェーズ13: prompt_versions router作成（ステップ60〜63）

#### ステップ60: routers/prompt_versions.py 作成
- **前提**: ステップ59完了
- **作業**: `src/backend/routers/prompt_versions.py` を作成。server.py:394-436 のエンドポイントを移行:
  ```python
  """Prompt versioning API routes."""
  from fastapi import APIRouter

  from config.container import Container
  from src.backend.database import UnitOfWork
  from src.models.api_schemas import RollbackRequest

  router = APIRouter(prefix="/api/prompt_versions", tags=["prompt_versions"])


  @router.get("/{book_id}")
  async def get_prompt_versions(book_id: int):
      # ... server.py:394-398 の実装をコピー ...


  @router.post("/{book_id}/rollback")
  async def rollback_prompt_version(book_id: int, req: RollbackRequest):
      # ... server.py:401-436 の実装をコピー ...
  ```
- **完了判定**: `python -c "from src.backend.routers.prompt_versions import router; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ61: server.pyからprompt_versionsエンドポイント削除
- **前提**: ステップ60完了
- **作業**: server.py:394-436 のエンドポイントを削除
- **完了判定**: server.pyが構文エラーなくインポート可能
- **想定エラー**: なし

#### ステップ62: server.pyにprompt_versions routerをinclude
- **前提**: ステップ61完了
- **作業**: server.pyの末尾に追加:
  ```python
  from src.backend.routers.prompt_versions import router as prompt_versions_router
  app.include_router(prompt_versions_router)
  ```
- **完了判定**: `python -c "from src.backend.server import app; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ63: prompt_versions routerの動作確認
- **前提**: ステップ62完了
- **作業**: `python -m pytest --collect-only -q` を実行
- **完了判定**: 438テスト収集・エラーゼロ
- **想定エラー**: なし

---

### フェーズ14: metrics router作成（ステップ64〜67）

#### ステップ64: routers/metrics.py 作成
- **前提**: ステップ63完了
- **作業**: `src/backend/routers/metrics.py` を作成。server.py:136-150, 850-857, 934-998 のエンドポイントを移行:
  ```python
  """Metrics API routes."""
  from typing import Any, Dict, Optional

  from fastapi import APIRouter

  from config.container import Container
  from src.backend.database import UnitOfWork

  router = APIRouter(tags=["metrics"])


  @router.get("/api/books/{book_id}/narrative_metrics", deprecated=True)
  async def get_narrative_metrics(book_id: int, branch_id: int = 1, ep_num: Optional[int] = None):
      """[非推奨] 新path版 /api/narrative_metrics/{book_id}/{branch_id} を使用してください。"""
      # ... server.py:136-150 の実装をコピー ...


  @router.get("/api/narrative_metrics/{book_id}/{branch_id}")
  async def get_narrative_metrics_trend(book_id: int, branch_id: int):
      # ... server.py:850-857 の実装をコピー ...


  @router.get("/api/prompt-metrics")
  async def get_prompt_metrics(limit: int = 100):
      # ... server.py:934-947 の実装をコピー ...


  @router.get("/api/prompt-metrics/template/{template_name}")
  async def get_prompt_metrics_by_template(template_name: str, limit: int = 50):
      # ... server.py:950-964 の実装をコピー ...


  @router.post("/api/prompt-metrics/save")
  async def save_prompt_metrics(request: Dict[str, Any]):
      # ... server.py:967-981 の実装をコピー ...


  @router.delete("/api/prompt-metrics")
  async def delete_old_prompt_metrics(days: int = 30):
      # ... server.py:984-998 の実装をコピー ...
  ```
- **完了判定**: `python -c "from src.backend.routers.metrics import router; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ65: server.pyからmetricsエンドポイント削除
- **前提**: ステップ64完了
- **作業**: server.py:136-150, 850-857, 934-998 のエンドポイントを削除
- **完了判定**: server.pyが構文エラーなくインポート可能
- **想定エラー**: なし

#### ステップ66: server.pyにmetrics routerをinclude
- **前提**: ステップ65完了
- **作業**: server.pyの末尾に追加:
  ```python
  from src.backend.routers.metrics import router as metrics_router
  app.include_router(metrics_router)
  ```
- **完了判定**: `python -c "from src.backend.server import app; print('OK')"` が成功
- **想定エラー**: なし

#### ステップ67: metrics routerの動作確認
- **前提**: ステップ66完了
- **作業**: `python -m pytest --collect-only -q` を実行
- **完了判定**: 438テスト収集・エラーゼロ
- **想定エラー**: なし

---

### フェーズ15: 残りエンドポイントのrouter化（ステップ68〜70）

#### ステップ68: chapters, bibles, misc router作成
- **前提**: ステップ67完了
- **作業**: 以下の3つのrouterファイルを作成:
  1. `src/backend/routers/chapters.py` — server.py:219-232, 790-808 を移行
  2. `src/backend/routers/bibles.py` — server.py:234-246 を移行
  3. `src/backend/routers/misc.py` — server.py:248-259, 545-563, 566-589, 750-766 を移行
- **完了判定**: 各routerが `python -c "from src.backend.routers.<name> import router; print('OK')"` でインポート可能
- **想定エラー**: なし

#### ステップ69: server.pyから残りエンドポイント削除
- **前提**: ステップ68完了
- **作業**: server.py:219-259, 545-589, 750-808 のエンドポイントを削除
- **完了判定**: server.pyが構文エラーなくインポート可能
- **想定エラー**: なし

#### ステップ70: server.pyに残りrouterをinclude
- **前提**: ステップ69完了
- **作業**: server.pyの末尾に追加:
  ```python
  from src.backend.routers.chapters import router as chapters_router
  from src.backend.routers.bibles import router as bibles_router
  from src.backend.routers.misc import router as misc_router
  app.include_router(chapters_router)
  app.include_router(bibles_router)
  app.include_router(misc_router)
  ```
- **完了判定**: `python -c "from src.backend.server import app; print('OK')"` が成功
- **想定エラー**: なし

---

### フェーズ16: 最終検証（ステップ71〜72）

#### ステップ71: 全テスト実行
- **前提**: ステップ70完了
- **作業**: `python -m pytest -x -q --timeout=60` を実行
- **完了判定**: ステップ2と同じ通過/失敗数（新規失敗なし）
- **想定エラー**: 新規失敗が出た場合 → 該当routerのimport文・エンドポイント定義を確認

#### ステップ72: 最終確認・完了判定
- **前提**: ステップ71完了
- **作業**: 以下を全て確認:
  1. `python -m pytest --collect-only -q` → 438テスト・エラーゼロ ✅
  2. server.pyの行数が200行以下であることを確認 ✅
  3. 各routerファイルが200行以下であることを確認 ✅
  4. OpenAPI定義でnarrative_metricsの重複が解消されていることを確認 ✅
  5. バックアップファイル（server.py.bak）を削除 ✅
- **完了判定**: ✅ 全改善案完了
- **想定エラー**: server.pyが200行を超える場合 → 残存するエンドポイント・import文を確認し、未移行のものをrouter化

---

## 📝 完了判定サマリー

| 改善案 | 完了判定 | 確認コマンド |
|--------|---------|-------------|
| 案1 | `pytest --collect-only` がエラーゼロ | `python -m pytest --collect-only -q` |
| 案2 | 重複ルート削除・OpenAPI一本化 | `python -c "from src.backend.server import app; [print(p) for p in app.openapi()['paths'] if 'narrative_metrics' in p]"` |
| 案3 | server.py 200行以下・各router 200行以下・テスト緑維持 | `(Get-Content src/backend/server.py | Measure-Object -Line).Lines` |

---

## ⚠️ 実装時の注意事項

1. **各ステップ完了後に必ず `python -m pytest --collect-only -q` を実行**し、エラーゼロを確認してから次へ進む
2. **server.pyの `app` オブジェクトは絶対に削除しない**（テストが `from src.backend.server import app` で参照している）
3. **routerのprefixは重複に注意**: `/api/books` のprefixを持つrouterで `/{book_id}/issues` を定義すると `/api/books/{book_id}/issues` になる
4. **import文は各routerファイル内で完結させる**: 循環importを避けるため、router間の依存は持たない
5. **_get_engine と _create_task はヘルパーモジュールに移動**: 複数routerから参照されるため
6. **デッドコード（server.py:858-860）は必ず削除**: 到達不能コードは静的解析の障害になる
